import pytest

from mzt.ir import Branch, ColonRef, Label, Literal, PrimRef, StringLit
from mzt.jit.assembler import (
    encode_b,
    encode_bl,
    encode_blr,
    encode_cbz,
    encode_ldp_post,
    encode_ldr_post_imm,
    encode_mov_from_sp,
    encode_ret,
    encode_stp_pre,
    encode_str_pre_imm,
    movz_imm64,
)
from mzt.jit.emitter import (
    JitEmitterError,
    compile_body,
    compile_body_to_bytes,
)
from mzt.jit.primitive_table import PrimitiveTable


PROLOGUE_WORDS = (
    encode_stp_pre(29, 30, 31, -16),
    encode_mov_from_sp(29),
)
EPILOGUE_WORDS = (
    encode_ldp_post(29, 30, 31, 16),
    encode_ret(),
)
PROLOGUE_LEN = 2
EPILOGUE_LEN = 2


def _table(name_to_addr: dict[str, int]) -> PrimitiveTable:
    return PrimitiveTable(name_to_addr)


def _empty_table() -> PrimitiveTable:
    return PrimitiveTable({})


def test_empty_body_is_just_prologue_and_epilogue():
    words = compile_body([], base_addr=0, primitives=_empty_table())
    assert words == [*PROLOGUE_WORDS, *EPILOGUE_WORDS], \
        "an empty body should compile to: stp/mov prologue, ldp/ret epilogue, nothing else"


def test_body_prologue_pushes_frame_pointer_and_link_register():
    words = compile_body([], base_addr=0, primitives=_empty_table())
    assert words[0] == encode_stp_pre(29, 30, 31, -16), \
        "prologue first instruction must save x29 and x30 with sp pre-decrement"


def test_body_prologue_sets_frame_pointer_to_sp():
    words = compile_body([], base_addr=0, primitives=_empty_table())
    assert words[1] == encode_mov_from_sp(29), \
        "prologue second instruction must set x29 = sp so debuggers can walk frames"


def test_body_epilogue_restores_frame_and_returns():
    words = compile_body([], base_addr=0, primitives=_empty_table())
    assert words[-2:] == [encode_ldp_post(29, 30, 31, 16), encode_ret()], \
        "epilogue must restore x29/x30 and return"


@pytest.mark.parametrize("value", [0, 1, 42, 255, 65535, 0xFFFF_FFFF, -1, -42, 0xCAFE_BABE_DEAD_BEEF])
def test_literal_cell_pushes_movz_tower_then_str_pre(value: int):
    words = compile_body([Literal(value)], base_addr=0, primitives=_empty_table())
    body = words[PROLOGUE_LEN:-EPILOGUE_LEN]
    expected_movs = movz_imm64(0, value)
    expected = [*expected_movs, encode_str_pre_imm(0, 19, -8)]
    assert body == expected, \
        f"Literal({value}) should compile to movz tower into x0 then str x0, [x19, #-8]!"


def test_literal_zero_uses_a_single_movz_then_str():
    words = compile_body([Literal(0)], base_addr=0, primitives=_empty_table())
    body = words[PROLOGUE_LEN:-EPILOGUE_LEN]
    assert len(body) == 2, \
        "Literal(0) should fit in two instructions: one movz x0, #0 plus one str"


def test_primref_inline_zero_emits_str_xzr_directly():
    words = compile_body([PrimRef("zero")], base_addr=0, primitives=_empty_table())
    body = words[PROLOGUE_LEN:-EPILOGUE_LEN]
    assert body == [encode_str_pre_imm(31, 19, -8)], \
        "inline primitive 'zero' should compile to a single str xzr, [x19, #-8]!"


def test_primref_non_inline_emits_movz_then_blr():
    plus_addr = 0x1_8000_4000
    table = _table({"+": plus_addr})

    words = compile_body([PrimRef("+")], base_addr=0x1000_0000, primitives=table)
    body = words[PROLOGUE_LEN:-EPILOGUE_LEN]

    expected = [*movz_imm64(16, plus_addr), encode_blr(16)]
    assert body == expected, \
        "PrimRef must load the absolute primitive address into x16 and blr; bl can't reach beyond ±128MB"


def test_primref_unknown_name_raises():
    with pytest.raises(JitEmitterError, match="primitive"):
        compile_body([PrimRef("not-a-primitive")], base_addr=0, primitives=_empty_table())


def test_primref_known_inline_without_jit_body_raises(mocker):
    mocker.patch("mzt.jit.emitter._INLINE_PRIMITIVE_WORDS", {})
    with pytest.raises(JitEmitterError, match="inline primitive"):
        compile_body([PrimRef("zero")], base_addr=0, primitives=_empty_table())


def test_colon_ref_emits_bl_to_user_word_address():
    base = 0x1000_0000
    foo_addr = 0x1000_2000
    words = compile_body(
        [ColonRef("foo")],
        base_addr=base,
        primitives=_empty_table(),
        word_addresses={"foo": foo_addr},
    )
    body_offset = base + 4 * PROLOGUE_LEN
    assert words[PROLOGUE_LEN] == encode_bl(foo_addr - body_offset), \
        "ColonRef should compile to bl into the previously-emitted word's body"


def test_colon_ref_unknown_name_raises():
    with pytest.raises(JitEmitterError, match="word"):
        compile_body(
            [ColonRef("undefined-word")],
            base_addr=0,
            primitives=_empty_table(),
            word_addresses={},
        )


def test_unconditional_branch_to_later_label_emits_b_with_forward_offset():
    cells = [
        Branch(target=1, conditional=False),
        Label(id=1),
    ]
    words = compile_body(cells, base_addr=0, primitives=_empty_table())
    branch_index = PROLOGUE_LEN
    label_index = PROLOGUE_LEN + 1
    expected_offset = (label_index - branch_index) * 4
    assert words[branch_index] == encode_b(expected_offset), \
        "unconditional Branch should encode as 'b' with the offset to the matching Label"


def test_unconditional_branch_back_emits_b_with_negative_offset():
    cells = [
        Label(id=1),
        Branch(target=1, conditional=False),
    ]
    words = compile_body(cells, base_addr=0, primitives=_empty_table())
    label_index = PROLOGUE_LEN
    branch_index = PROLOGUE_LEN
    expected_offset = (label_index - branch_index) * 4
    assert words[PROLOGUE_LEN] == encode_b(expected_offset), \
        "back-branch should produce a negative or zero offset relative to its own position"


def test_conditional_branch_emits_pop_and_cbz_to_target():
    cells = [
        Branch(target=2, conditional=True),
        Label(id=2),
    ]
    words = compile_body(cells, base_addr=0, primitives=_empty_table())
    pop_index = PROLOGUE_LEN
    cbz_index = pop_index + 1
    label_index = cbz_index + 1
    assert words[pop_index] == encode_ldr_post_imm(0, 19, 8), \
        "conditional branch must first pop TOS into x0 (post-increment ldr)"
    assert words[cbz_index] == encode_cbz(0, (label_index - cbz_index) * 4), \
        "conditional branch then cbz x0 to the target label"


def test_label_does_not_emit_an_instruction():
    cells = [Label(id=1), Label(id=2)]
    words = compile_body(cells, base_addr=0, primitives=_empty_table())
    assert len(words) == PROLOGUE_LEN + EPILOGUE_LEN, \
        "Label cells are positions in the instruction stream; they emit no bytes"


def test_branch_to_undefined_label_raises():
    cells = [Branch(target=99, conditional=False)]
    with pytest.raises(JitEmitterError, match="label"):
        compile_body(cells, base_addr=0, primitives=_empty_table())


def test_compose_literal_then_primitive_then_return():
    plus = 0x1_5000_0000
    cells = [Literal(1), Literal(2), PrimRef("+")]
    words = compile_body(cells, base_addr=0x4000_0000, primitives=_table({"+": plus}))

    expected = [
        *PROLOGUE_WORDS,
        *movz_imm64(0, 1),
        encode_str_pre_imm(0, 19, -8),
        *movz_imm64(0, 2),
        encode_str_pre_imm(0, 19, -8),
        *movz_imm64(16, plus),
        encode_blr(16),
        *EPILOGUE_WORDS,
    ]
    assert words == expected, \
        "1 2 + should compile to two literal pushes followed by movz x16 / blr x16 to '+'"


def test_compile_body_to_bytes_is_little_endian_packed():
    words = [encode_ret()]
    raw = bytes()
    for w in words:
        raw += w.to_bytes(4, "little")
    body = compile_body_to_bytes([], base_addr=0, primitives=_empty_table())
    assert len(body) % 4 == 0, "byte length must be a multiple of 4 (instruction-aligned)"
    assert body.endswith(raw), "the last instruction must be ret, packed little-endian"


@pytest.mark.parametrize(
    "unsupported",
    [StringLit("hi"), object()],
    ids=["StringLit", "raw object"],
)
def test_unsupported_cell_raises(unsupported):
    with pytest.raises(JitEmitterError):
        compile_body([unsupported], base_addr=0, primitives=_empty_table())


def test_loop_pattern_begin_until_resolves_back_branch():
    dup_addr = 0x1_2345_0000
    cells = [
        Label(id=10),
        PrimRef("dup"),
        Branch(target=10, conditional=True),
    ]
    table = _table({"dup": dup_addr})
    words = compile_body(cells, base_addr=0, primitives=table)

    primref_len = len(movz_imm64(16, dup_addr)) + 1
    label_index = PROLOGUE_LEN
    cbz_index = PROLOGUE_LEN + primref_len + 1
    expected_cbz_offset = (label_index - cbz_index) * 4

    assert words[cbz_index] == encode_cbz(0, expected_cbz_offset), \
        "begin-until back-branch should encode a negative offset from cbz to the begin label"


def test_if_else_then_pattern_resolves_both_branches():
    cells = [
        PrimRef("zero"),
        Branch(target=1, conditional=True),
        Literal(10),
        Branch(target=2, conditional=False),
        Label(id=1),
        Literal(20),
        Label(id=2),
    ]
    words = compile_body(cells, base_addr=0, primitives=_empty_table())

    cond_branch_index = PROLOGUE_LEN + 1 + 1
    skip_branch_index = cond_branch_index + 1 + len(movz_imm64(0, 10)) + 1
    label_1_index = skip_branch_index + 1
    label_2_index = label_1_index + len(movz_imm64(0, 20)) + 1

    assert words[cond_branch_index] == encode_cbz(0, (label_1_index - cond_branch_index) * 4), \
        "the if-conditional-branch should jump to the else branch (label 1) when zero"
    assert words[skip_branch_index] == encode_b((label_2_index - skip_branch_index) * 4), \
        "after the then-branch, an unconditional b should skip the else block"


def test_word_addresses_default_to_empty_when_omitted():
    words = compile_body([Literal(7)], base_addr=0, primitives=_empty_table())
    assert len(words) > 0, "compile_body should accept omitted word_addresses kwarg"
