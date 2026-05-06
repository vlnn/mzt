import ctypes
import sys

import pytest

from mzt.jit import _libc
from mzt.jit.region import (
    INSTR_SIZE,
    PAGE_SIZE,
    JitRegion,
    JitRegionFull,
    JitWriteError,
)


RET_X30 = 0xD65F03C0


class FakeLibc:
    def __init__(self):
        self._buffers: dict[int, ctypes.Array] = {}
        self.allocations: list[int] = []
        self.deallocations: list[tuple[int, int]] = []
        self.writable_states: list[bool] = []
        self.icache_flushes: list[tuple[int, int]] = []

    def allocate_jit(self, size: int) -> int:
        buf = ctypes.create_string_buffer(size)
        addr = ctypes.addressof(buf)
        self._buffers[addr] = buf
        self.allocations.append(size)
        return addr

    def deallocate(self, base: int, size: int) -> None:
        self.deallocations.append((base, size))
        self._buffers.pop(base, None)

    def set_writable(self, writable: bool) -> None:
        self.writable_states.append(writable)

    def flush_icache(self, base: int, size: int) -> None:
        self.icache_flushes.append((base, size))


@pytest.fixture
def fake_libc():
    return FakeLibc()


@pytest.fixture
def region(fake_libc):
    r = JitRegion(size=PAGE_SIZE, libc=fake_libc)
    yield r
    r.close()


def test_constructor_rounds_size_up_to_page_boundary(fake_libc):
    region = JitRegion(size=1, libc=fake_libc)
    try:
        assert region.size == PAGE_SIZE, \
            f"size 1 should round up to one page ({PAGE_SIZE}); got {region.size}"
    finally:
        region.close()


@pytest.mark.parametrize("requested,expected", [
    (1, PAGE_SIZE),
    (PAGE_SIZE - 1, PAGE_SIZE),
    (PAGE_SIZE, PAGE_SIZE),
    (PAGE_SIZE + 1, 2 * PAGE_SIZE),
    (3 * PAGE_SIZE, 3 * PAGE_SIZE),
])
def test_size_rounds_to_page_multiple(fake_libc, requested, expected):
    region = JitRegion(size=requested, libc=fake_libc)
    try:
        assert region.size == expected, \
            f"size {requested} should round up to {expected}; got {region.size}"
    finally:
        region.close()


def test_constructor_calls_allocate_with_rounded_size(fake_libc):
    JitRegion(size=1, libc=fake_libc).close()
    assert fake_libc.allocations == [PAGE_SIZE], \
        f"constructor should request {PAGE_SIZE} bytes from libc; got {fake_libc.allocations}"


def test_base_is_nonzero_after_construction(region):
    assert region.base != 0, \
        "base address should be the live mmap result, not zero"


def test_cursor_starts_at_zero(region):
    assert region.cursor == 0, \
        f"freshly allocated region should have cursor at 0; got {region.cursor}"


def test_here_starts_at_base(region):
    assert region.here() == region.base, \
        "here() with empty region should equal base"


def test_remaining_starts_at_size(region):
    assert region.remaining == region.size, \
        f"empty region should have full size remaining; got {region.remaining}"


def test_append_outside_writable_block_raises(region):
    with pytest.raises(JitWriteError, match="writable"):
        region.append_u32(RET_X30)


def test_append_inside_writable_block_advances_cursor(region):
    with region.writable():
        region.append_u32(RET_X30)
    assert region.cursor == INSTR_SIZE, \
        f"one append should advance cursor by {INSTR_SIZE}; got {region.cursor}"


def test_append_returns_address_just_written(region):
    base_before = region.base
    with region.writable():
        addr = region.append_u32(RET_X30)
    assert addr == base_before, \
        f"first append should return base address {base_before:#x}; got {addr:#x}"


@pytest.mark.parametrize("count", [1, 2, 5, 16])
def test_repeated_appends_advance_cursor_by_4_each(region, count):
    with region.writable():
        for _ in range(count):
            region.append_u32(RET_X30)
    assert region.cursor == count * INSTR_SIZE, \
        f"{count} appends should leave cursor at {count * INSTR_SIZE}; got {region.cursor}"


def test_appended_bytes_are_readable_back(region):
    with region.writable():
        addr = region.append_u32(RET_X30)
    assert region.read_u32(addr) == RET_X30, \
        f"appended u32 should round-trip; wrote {RET_X30:#x}, read back {region.read_u32(addr):#x}"


def test_append_writes_little_endian(region):
    with region.writable():
        addr = region.append_u32(0x12345678)
    raw = bytes((ctypes.c_ubyte * 4).from_address(addr))
    assert raw == b"\x78\x56\x34\x12", \
        f"u32 should be written little-endian; got {raw!r}"


def test_append_bytes_outside_writable_block_raises(region):
    with pytest.raises(JitWriteError, match="writable"):
        region.append_bytes(b"\x00\x00\x00\x00")


def test_append_bytes_writes_payload_verbatim(region):
    payload = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    with region.writable():
        addr = region.append_bytes(payload)
    raw = bytes((ctypes.c_ubyte * len(payload)).from_address(addr))
    assert raw == payload, \
        f"payload should be written verbatim; got {raw!r}"


def test_append_bytes_advances_cursor_by_payload_size(region):
    with region.writable():
        region.append_bytes(b"\x00" * 16)
    assert region.cursor == 16, \
        f"16-byte payload should advance cursor by 16; got {region.cursor}"


def test_append_bytes_rejects_unaligned_payload(region):
    with region.writable():
        with pytest.raises(JitWriteError, match="aligned"):
            region.append_bytes(b"\x00\x00\x00")


def test_writable_context_toggles_writable_state(region, fake_libc):
    with region.writable():
        pass
    assert fake_libc.writable_states == [True, False], \
        f"writable() should set writable on entry and unset on exit; got {fake_libc.writable_states}"


def test_writable_context_unsets_even_if_body_raises(region, fake_libc):
    with pytest.raises(RuntimeError, match="boom"):
        with region.writable():
            raise RuntimeError("boom")
    assert fake_libc.writable_states == [True, False], \
        f"writable state should be cleared even on exception; got {fake_libc.writable_states}"


def test_writable_context_flushes_icache_on_exit(region, fake_libc):
    with region.writable():
        region.append_u32(RET_X30)
    assert fake_libc.icache_flushes == [(region.base, region.size)], \
        f"icache should be flushed once on exit covering full region; got {fake_libc.icache_flushes}"


def test_two_writable_blocks_flush_twice(region, fake_libc):
    with region.writable():
        region.append_u32(RET_X30)
    with region.writable():
        region.append_u32(RET_X30)
    assert len(fake_libc.icache_flushes) == 2, \
        f"two writable blocks should produce two icache flushes; got {len(fake_libc.icache_flushes)}"


def test_append_after_writable_block_exits_raises(region):
    with region.writable():
        region.append_u32(RET_X30)
    with pytest.raises(JitWriteError):
        region.append_u32(RET_X30)


def test_append_capacity_exhaustion_raises(fake_libc):
    region = JitRegion(size=PAGE_SIZE, libc=fake_libc)
    instr_count = region.size // INSTR_SIZE
    try:
        with region.writable():
            for _ in range(instr_count):
                region.append_u32(RET_X30)
            with pytest.raises(JitRegionFull, match="remain"):
                region.append_u32(RET_X30)
    finally:
        region.close()


def test_append_u32_truncates_to_32_bits(region):
    with region.writable():
        addr = region.append_u32(0x1_FFFF_FFFF)
    assert region.read_u32(addr) == 0xFFFFFFFF, \
        "append_u32 should mask the input to 32 bits"


def test_append_u32_many_writes_each_word_in_order(region):
    words = [0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC]
    with region.writable():
        first = region.append_u32_many(words)
    for offset, expected in enumerate(words):
        addr = first + offset * INSTR_SIZE
        assert region.read_u32(addr) == expected, \
            f"word at offset {offset} should be {expected:#x}; got {region.read_u32(addr):#x}"


def test_append_u32_many_returns_address_of_first_word(region):
    base = region.base
    with region.writable():
        first = region.append_u32_many([RET_X30, RET_X30])
    assert first == base, \
        f"append_u32_many should return base of first word ({base:#x}); got {first:#x}"


def test_patch_u32_overwrites_existing_word(region):
    with region.writable():
        addr = region.append_u32(0xDEADBEEF)
        region.patch_u32(addr, RET_X30)
    assert region.read_u32(addr) == RET_X30, \
        "patch_u32 should overwrite the previous instruction in place"


def test_patch_u32_outside_writable_raises(region):
    with region.writable():
        addr = region.append_u32(RET_X30)
    with pytest.raises(JitWriteError):
        region.patch_u32(addr, RET_X30)


def test_patch_u32_outside_region_raises(region):
    with region.writable():
        with pytest.raises(ValueError, match="outside region"):
            region.patch_u32(region.base + region.size + 4, RET_X30)


def test_close_calls_deallocate_with_base_and_size(fake_libc):
    region = JitRegion(size=PAGE_SIZE, libc=fake_libc)
    base = region.base
    size = region.size
    region.close()
    assert fake_libc.deallocations == [(base, size)], \
        f"close() should call deallocate(base={base:#x}, size={size}); got {fake_libc.deallocations}"


def test_close_is_idempotent(fake_libc):
    region = JitRegion(size=PAGE_SIZE, libc=fake_libc)
    region.close()
    region.close()
    assert len(fake_libc.deallocations) == 1, \
        "double close should free at most once"


def test_context_manager_closes_on_normal_exit(fake_libc):
    with JitRegion(size=PAGE_SIZE, libc=fake_libc):
        pass
    assert len(fake_libc.deallocations) == 1, \
        "context-manager exit should deallocate exactly once"


def test_context_manager_closes_on_exception(fake_libc):
    with pytest.raises(RuntimeError, match="boom"):
        with JitRegion(size=PAGE_SIZE, libc=fake_libc):
            raise RuntimeError("boom")
    assert len(fake_libc.deallocations) == 1, \
        "context-manager exit on exception should still deallocate"


def test_constructor_uses_system_libc_when_none_passed(mocker):
    if not _libc.is_supported_platform():
        with pytest.raises(RuntimeError, match="JIT requires"):
            JitRegion(size=PAGE_SIZE)
        return
    spy_loader = mocker.patch.object(
        _libc, "load_system_libc", return_value=FakeLibc(),
    )
    JitRegion(size=PAGE_SIZE).close()
    assert spy_loader.call_count == 1, \
        "default constructor should defer to load_system_libc once"


pytestmark_platform = pytest.mark.skipif(
    not _libc.is_supported_platform(),
    reason=f"JIT region needs Apple Silicon: {_libc.unsupported_reason()}",
)


@pytestmark_platform
def test_real_jit_region_can_allocate_and_free():
    region = JitRegion(size=PAGE_SIZE)
    assert region.base != 0, \
        "MAP_JIT mmap should return a valid (non-null) address"
    region.close()


@pytestmark_platform
def test_real_jit_region_executes_a_ret_only_function():
    with JitRegion(size=PAGE_SIZE) as region:
        with region.writable():
            addr = region.append_u32(RET_X30)
        func = ctypes.CFUNCTYPE(None)(addr)
        func()
