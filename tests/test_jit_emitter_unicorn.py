import pytest

from mzt.ir import Branch, ColonRef, Label, Literal, PrimRef
from mzt.jit.assembler import (
    encode_add_reg,
    encode_ldr_post_imm,
    encode_ret,
    encode_str_pre_imm,
    words_to_bytes,
)
from mzt.jit.emitter import compile_body_to_bytes
from mzt.jit.primitive_table import PrimitiveTable

from tests.jit_runner import (
    AVAILABLE,
    PRIM_BASE,
    UNAVAILABLE_REASON,
    JIT_BASE,
    run_jit_body,
)


pytestmark = pytest.mark.skipif(not AVAILABLE, reason=UNAVAILABLE_REASON or "unicorn unavailable")


def _stub_plus_bytes() -> bytes:
    return words_to_bytes([
        encode_ldr_post_imm(0, 19, 8),
        encode_ldr_post_imm(1, 19, 8),
        encode_add_reg(0, 1, 0),
        encode_str_pre_imm(0, 19, -8),
        encode_ret(),
    ])


def _stub_dup_bytes() -> bytes:
    return words_to_bytes([
        encode_ldr_post_imm(0, 19, 0),
        encode_str_pre_imm(0, 19, -8),
        encode_ret(),
    ])


def _stub_drop_bytes() -> bytes:
    return words_to_bytes([
        encode_ldr_post_imm(0, 19, 8),
        encode_ret(),
    ])


def _empty_table() -> PrimitiveTable:
    return PrimitiveTable({})


@pytest.mark.parametrize("value", [0, 1, 7, 42, 0xFFFF, 0xCAFE_BABE, -1, -42])
def test_literal_lands_on_data_stack(value: int):
    body = compile_body_to_bytes([Literal(value)], base_addr=JIT_BASE, primitives=_empty_table())
    result = run_jit_body(body)
    assert result == [value], \
        f"Literal({value}) should leave exactly that value on top of the data stack"


def test_two_literals_push_in_order():
    body = compile_body_to_bytes(
        [Literal(7), Literal(11)],
        base_addr=JIT_BASE,
        primitives=_empty_table(),
    )
    result = run_jit_body(body)
    assert result == [7, 11], \
        "literals should push left-to-right; 7 then 11 leaves 7 below 11 on the stack"


def test_inline_zero_pushes_zero_via_str_xzr():
    body = compile_body_to_bytes(
        [PrimRef("zero")],
        base_addr=JIT_BASE,
        primitives=_empty_table(),
    )
    result = run_jit_body(body)
    assert result == [0], \
        "inline 'zero' primitive should push 0 (str xzr is shorthand for 'push 0')"


def test_primref_call_reaches_primitive_stub_and_returns():
    plus_addr = PRIM_BASE
    table = PrimitiveTable({"+": plus_addr})
    body = compile_body_to_bytes(
        [Literal(2), Literal(3), PrimRef("+")],
        base_addr=JIT_BASE,
        primitives=table,
    )
    result = run_jit_body(body, primitive_stubs={plus_addr: _stub_plus_bytes()})
    assert result == [5], \
        "movz x16, +addr; blr x16 must transfer to the stub, which adds 2+3 and returns"


def test_primref_call_with_far_address():
    plus_addr = 0xCAFE_0000_0000
    table = PrimitiveTable({"+": plus_addr})
    body = compile_body_to_bytes(
        [Literal(10), Literal(20), PrimRef("+")],
        base_addr=JIT_BASE,
        primitives=table,
    )
    result = run_jit_body(body, primitive_stubs={plus_addr: _stub_plus_bytes()})
    assert result == [30], \
        "even with a primitive 200+ TB away, movz+blr must reach (bl could not)"


def test_dup_primitive_via_jit():
    dup_addr = PRIM_BASE
    table = PrimitiveTable({"dup": dup_addr})
    body = compile_body_to_bytes(
        [Literal(99), PrimRef("dup")],
        base_addr=JIT_BASE,
        primitives=table,
    )
    result = run_jit_body(body, primitive_stubs={dup_addr: _stub_dup_bytes()})
    assert result == [99, 99], \
        "after pushing 99 and calling dup, the stack should hold two copies of 99"


def test_chained_primitive_calls():
    plus_addr = PRIM_BASE
    drop_addr = PRIM_BASE + 0x1000
    table = PrimitiveTable({"+": plus_addr, "drop": drop_addr})
    body = compile_body_to_bytes(
        [Literal(1), Literal(2), PrimRef("+"), Literal(99), PrimRef("drop")],
        base_addr=JIT_BASE,
        primitives=table,
    )
    stubs = {
        plus_addr: _stub_plus_bytes(),
        drop_addr: _stub_drop_bytes(),
    }
    result = run_jit_body(body, primitive_stubs=stubs)
    assert result == [3], \
        "1 2 + 99 drop should leave just 3; chained primitive calls must compose correctly"


def test_unconditional_branch_skips_intervening_code():
    body = compile_body_to_bytes(
        [
            Literal(1),
            Branch(target=99, conditional=False),
            Literal(2),
            Label(id=99),
            Literal(3),
        ],
        base_addr=JIT_BASE,
        primitives=_empty_table(),
    )
    result = run_jit_body(body)
    assert result == [1, 3], \
        "the unconditional branch should jump over Literal(2); only 1 and 3 should land on the stack"


def test_conditional_branch_taken_when_top_is_zero():
    body = compile_body_to_bytes(
        [
            Literal(5),
            PrimRef("zero"),
            Branch(target=10, conditional=True),
            Literal(99),
            Label(id=10),
            Literal(7),
        ],
        base_addr=JIT_BASE,
        primitives=_empty_table(),
    )
    result = run_jit_body(body)
    assert result == [5, 7], \
        "with TOS=0 the conditional cbz should take the branch, skipping Literal(99)"


def test_conditional_branch_not_taken_when_top_is_nonzero():
    body = compile_body_to_bytes(
        [
            Literal(5),
            Literal(1),
            Branch(target=10, conditional=True),
            Literal(99),
            Label(id=10),
            Literal(7),
        ],
        base_addr=JIT_BASE,
        primitives=_empty_table(),
    )
    result = run_jit_body(body)
    assert result == [5, 99, 7], \
        "with TOS=1 the cbz should fall through, so Literal(99) executes before Literal(7)"


def test_colon_ref_calls_another_jit_word():
    plus_addr = PRIM_BASE
    table = PrimitiveTable({"+": plus_addr})

    inner_base = JIT_BASE + 0x1000
    inner = compile_body_to_bytes(
        [Literal(40), Literal(2), PrimRef("+")],
        base_addr=inner_base,
        primitives=table,
    )

    outer_base = JIT_BASE
    outer = compile_body_to_bytes(
        [ColonRef("inner")],
        base_addr=outer_base,
        primitives=table,
        word_addresses={"inner": inner_base},
    )

    combined = bytearray(_pad_to(0x1000))
    combined[: len(outer)] = outer
    combined[0x1000 : 0x1000 + len(inner)] = inner

    result = run_jit_body(
        bytes(combined),
        primitive_stubs={plus_addr: _stub_plus_bytes()},
    )
    assert result == [42], \
        "outer should bl into inner, which leaves 42 on the stack and returns to outer"


def _pad_to(size: int) -> bytes:
    return b"\0" * size
