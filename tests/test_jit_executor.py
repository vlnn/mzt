import ctypes
import sys
from pathlib import Path

import pytest

from mzt.ir import ColonRef, Literal, PrimRef
from mzt.jit.assembler import (
    encode_add_reg,
    encode_ldr_post_imm,
    encode_ret,
    encode_str_pre_imm,
    words_to_bytes,
)
from mzt.jit.executor import JitExecutor
from mzt.jit.primitive_table import PrimitiveTable
from mzt.jit.region import JitRegion


DSTACK_TOP_FAKE = 0x2000_0000
RSTACK_TOP_FAKE = 0x3000_0000


class _FakeMemory:
    def __init__(self, ranges):
        self._buf = {}
        self._ranges = ranges

    def write_u64(self, address: int, value: int) -> None:
        self._buf[address] = value

    def read_u64(self, address: int) -> int:
        return self._buf.get(address, 0)


class _ScriptedTrampoline:
    def __init__(self):
        self.calls: list[tuple[int, int, int]] = []
        self._dx19_after = 0
        self._dx20_after = 0
        self._mem_writes: list[tuple[int, int]] = []

    def will_decrement_x19_by(self, delta: int):
        self._dx19_after = delta
        return self

    def will_decrement_x20_by(self, delta: int):
        self._dx20_after = delta
        return self

    def will_write_dstack(self, *value_pairs):
        self._mem_writes = list(value_pairs)
        return self

    def __call__(self, x19: int, x20: int, body_addr: int) -> tuple[int, int]:
        self.calls.append((x19, x20, body_addr))
        return x19 - self._dx19_after, x20 - self._dx20_after


def _build_executor(*, primitives=None, trampoline=None, region=None,
                    dstack_top=DSTACK_TOP_FAKE, rstack_top=RSTACK_TOP_FAKE):
    return JitExecutor(
        primitives=primitives or PrimitiveTable({}),
        region=region or _make_fake_region(),
        trampoline=trampoline or _ScriptedTrampoline(),
        dstack_top=dstack_top,
        rstack_top=rstack_top,
    )


def _make_fake_region():
    from tests.test_jit_region import FakeLibc
    return JitRegion(libc=FakeLibc())


def test_initial_state_points_at_stack_tops():
    exec_ = _build_executor()
    assert exec_.x19 == DSTACK_TOP_FAKE, "x19 starts at the data-stack top"
    assert exec_.x20 == RSTACK_TOP_FAKE, "x20 starts at the return-stack top"


def test_word_addresses_starts_empty():
    exec_ = _build_executor()
    assert exec_.word_addresses == {}, "no JIT'd words have been compiled yet"


def test_compile_writes_body_into_region_and_records_address():
    exec_ = _build_executor()
    addr = exec_.compile("foo", [Literal(7)])
    assert addr == exec_.region.base, "first compile should land at the region base"
    assert exec_.word_addresses["foo"] == addr, \
        "compile should remember 'foo' -> its address for later ColonRef resolution"
    assert exec_.region.cursor > 0, "compile should advance the region cursor"


def test_compile_two_bodies_places_them_sequentially():
    exec_ = _build_executor()
    addr_a = exec_.compile("a", [Literal(1)])
    addr_b = exec_.compile("b", [Literal(2)])
    assert addr_b > addr_a, "second body should land after the first"
    assert exec_.word_addresses == {"a": addr_a, "b": addr_b}, \
        "both compiled words should be tracked in word_addresses"


def test_compile_emits_executable_code_starting_with_prologue(mocker):
    from mzt.jit.assembler import encode_mov_from_sp, encode_stp_pre
    exec_ = _build_executor()
    addr = exec_.compile("foo", [])
    first = exec_.region.read_u32(addr)
    second = exec_.region.read_u32(addr + 4)
    assert first == encode_stp_pre(29, 30, 31, -16), \
        "compiled body must start with the AAPCS64 prologue stp"
    assert second == encode_mov_from_sp(29), \
        "second instruction must set x29 = sp"


def test_execute_passes_current_state_to_trampoline():
    tramp = _ScriptedTrampoline()
    exec_ = _build_executor(trampoline=tramp)
    addr = exec_.compile("foo", [Literal(42)])
    exec_.execute(addr)
    assert tramp.calls == [(DSTACK_TOP_FAKE, RSTACK_TOP_FAKE, addr)], \
        "execute should hand the trampoline (x19, x20, body_addr)"


def test_execute_updates_x19_and_x20_from_trampoline_result():
    tramp = _ScriptedTrampoline().will_decrement_x19_by(8).will_decrement_x20_by(16)
    exec_ = _build_executor(trampoline=tramp)
    addr = exec_.compile("foo", [Literal(42)])
    exec_.execute(addr)
    assert exec_.x19 == DSTACK_TOP_FAKE - 8, \
        "after execute, x19 must reflect what the trampoline returned"
    assert exec_.x20 == RSTACK_TOP_FAKE - 16, \
        "after execute, x20 must reflect what the trampoline returned"


def test_execute_unknown_address_raises(mocker):
    tramp = _ScriptedTrampoline()
    exec_ = _build_executor(trampoline=tramp)
    with pytest.raises(KeyError):
        exec_.execute_word("never-compiled")


def test_execute_word_looks_up_address_by_name():
    tramp = _ScriptedTrampoline()
    exec_ = _build_executor(trampoline=tramp)
    addr = exec_.compile("greet", [Literal(99)])
    exec_.execute_word("greet")
    assert tramp.calls == [(DSTACK_TOP_FAKE, RSTACK_TOP_FAKE, addr)], \
        "execute_word should resolve the name and call the trampoline with that address"


def test_reset_restores_initial_x19_and_x20_but_keeps_compiled_words():
    tramp = _ScriptedTrampoline().will_decrement_x19_by(16)
    exec_ = _build_executor(trampoline=tramp)
    addr = exec_.compile("foo", [Literal(1)])
    exec_.execute(addr)
    assert exec_.x19 != DSTACK_TOP_FAKE, "execute should have moved x19"
    exec_.reset()
    assert exec_.x19 == DSTACK_TOP_FAKE, "reset should put x19 back at the dstack top"
    assert exec_.x20 == RSTACK_TOP_FAKE, "reset should put x20 back at the rstack top"
    assert exec_.word_addresses == {"foo": addr}, \
        "reset must NOT clear word_addresses; the JIT'd code is still live in the region"


def test_compile_uses_word_addresses_for_colon_refs():
    exec_ = _build_executor()
    inner_addr = exec_.compile("inner", [Literal(40)])
    outer_addr = exec_.compile("outer", [ColonRef("inner")])
    from mzt.jit.assembler import encode_bl
    bl_word = exec_.region.read_u32(outer_addr + 8)
    expected_offset = inner_addr - (outer_addr + 8)
    assert bl_word == encode_bl(expected_offset), \
        "outer's bl to inner should encode a relative offset to the prior word's address"


def test_read_dstack_returns_empty_when_x19_at_top():
    exec_ = _build_executor()
    assert exec_.read_dstack() == [], \
        "with x19 at dstack_top, the data stack is empty"


def test_read_dstack_walks_from_x19_to_top_reading_each_cell(mocker):
    exec_ = _build_executor()
    exec_.x19 = DSTACK_TOP_FAKE - 24

    def fake_string_at(addr, n):
        index = (DSTACK_TOP_FAKE - addr) // 8 - 1
        return [10, 20, 30][index].to_bytes(8, "little", signed=True)

    mocker.patch("mzt.jit.executor.ctypes.string_at", side_effect=fake_string_at)
    stack = exec_.read_dstack()
    assert stack == [10, 20, 30], \
        "read_dstack should walk from x19 toward top, returning bottom-to-top order"


def test_read_dstack_handles_negative_values(mocker):
    exec_ = _build_executor()
    exec_.x19 = DSTACK_TOP_FAKE - 8
    mocker.patch(
        "mzt.jit.executor.ctypes.string_at",
        return_value=(-7).to_bytes(8, "little", signed=True),
    )
    assert exec_.read_dstack() == [-7], \
        "stack values are signed 64-bit; -7 must round-trip cleanly"


def test_read_rstack_walks_from_x20_to_rstack_top(mocker):
    exec_ = _build_executor()
    exec_.x20 = RSTACK_TOP_FAKE - 8
    mocker.patch(
        "mzt.jit.executor.ctypes.string_at",
        return_value=(99).to_bytes(8, "little"),
    )
    assert exec_.read_rstack() == [99], \
        "read_rstack should walk from x20 toward rstack_top"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_open_builds_dylib_and_returns_ready_executor(tmp_path):
    lib_path = tmp_path / "libmzt_host.dylib"
    with JitExecutor.open(host_lib_path=lib_path) as executor:
        assert executor.x19 > 0, "after open, x19 should be set to a real dstack top address"
        assert executor.x20 > 0, "after open, x20 should be set to a real rstack top address"
        assert executor.x19 != executor.x20, \
            "data and return stack tops must be distinct"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_compile_and_execute_two_three_plus_leaves_five_on_dstack(tmp_path):
    lib_path = tmp_path / "libmzt_host.dylib"
    with JitExecutor.open(host_lib_path=lib_path) as executor:
        addr = executor.compile("test", [Literal(2), Literal(3), PrimRef("+")])
        executor.execute(addr)
        assert executor.read_dstack() == [5], \
            "after running 2 3 +, the data stack should hold exactly the value 5"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_compile_and_execute_colon_word_via_colon_ref(tmp_path):
    lib_path = tmp_path / "libmzt_host.dylib"
    with JitExecutor.open(host_lib_path=lib_path) as executor:
        executor.compile("forty-two", [Literal(40), Literal(2), PrimRef("+")])
        addr = executor.compile("call-it", [ColonRef("forty-two")])
        executor.execute(addr)
        assert executor.read_dstack() == [42], \
            "outer JIT'd word should bl into the inner one and inherit its stack effect"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_reset_after_real_execution_restores_empty_stack(tmp_path):
    lib_path = tmp_path / "libmzt_host.dylib"
    with JitExecutor.open(host_lib_path=lib_path) as executor:
        addr = executor.compile("push-and-leave", [Literal(7), Literal(8)])
        executor.execute(addr)
        assert executor.read_dstack() == [7, 8], "preconditions: stack should hold 7 then 8"
        executor.reset()
        assert executor.read_dstack() == [], \
            "reset should put x19 back at dstack_top, making the stack appear empty"
