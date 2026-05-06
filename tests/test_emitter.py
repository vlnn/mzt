import pytest

from mzt.emitter import emit_program
from mzt.ir import Branch, ColonDef, ColonRef, Label, Literal, PrimRef


def _emit_main(*body):
    return emit_program([ColonDef("main", tuple(body))])


def test_each_definition_gets_a_word_label():
    asm = emit_program([
        ColonDef("helper", (Literal(1),)),
        ColonDef("main", (ColonRef("helper"),)),
    ])
    assert "_word_helper:" in asm, "every colon def should produce a _word_<name>: label"
    assert "_word_main:" in asm, "every colon def should produce a _word_<name>: label"


def test_colon_word_saves_and_restores_frame():
    asm = _emit_main(Literal(0))
    assert "stp     x29, x30, [sp, #-16]!" in asm, \
        "every colon word should save x29/x30 on entry"
    assert "ldp     x29, x30, [sp], #16" in asm, \
        "every colon word should restore x29/x30 before ret"


@pytest.mark.parametrize("value", [0, 1, 42, -7, 9999999999])
def test_literal_uses_ldr_equals_form(value):
    asm = _emit_main(Literal(value))
    assert f"ldr     x0, ={value}" in asm, \
        f"Literal({value}) should compile via ldr x0, = form for the literal pool"


def test_literal_pushes_via_pre_decrement():
    asm = _emit_main(Literal(7))
    assert "str     x0, [x19, #-8]!" in asm, \
        "literal push should pre-decrement x19 and store the value"


@pytest.mark.parametrize(
    "name,expected_call",
    [
        ("dup",    "bl      _dup"),
        ("drop",   "bl      _drop"),
        ("swap",   "bl      _swap"),
        ("over",   "bl      _over"),
        ("nip",    "bl      _nip"),
        ("rot",    "bl      _rot"),
        ("+",      "bl      _plus"),
        ("-",      "bl      _minus"),
        ("*",      "bl      _star"),
        ("/mod",   "bl      _divmod"),
        ("=",      "bl      _eq"),
        ("<",      "bl      _lt"),
        (">",      "bl      _gt"),
        ("0=",     "bl      _zeq"),
        ("and",    "bl      _and"),
        ("or",     "bl      _or"),
        ("xor",    "bl      _xor"),
        ("invert", "bl      _invert"),
        ("negate", "bl      _negate"),
        ("abs",    "bl      _abs"),
        (".",      "bl      _dot"),
        ("emit",   "bl      _emit"),
        ("cr",     "bl      _cr"),
        (">r",     "bl      _to_r"),
        ("r>",     "bl      _r_from"),
        ("r@",     "bl      _r_fetch"),
    ],
)
def test_primitive_compiles_to_bl(name, expected_call):
    asm = _emit_main(PrimRef(name))
    assert expected_call in asm, \
        f"PrimRef({name!r}) should emit {expected_call!r} per subroutine threading"


def test_colon_ref_calls_word_label():
    asm = emit_program([
        ColonDef("helper", (Literal(1),)),
        ColonDef("main", (ColonRef("helper"),)),
    ])
    assert "bl      _word_helper" in asm, \
        "ColonRef should compile to bl _word_<name>"


@pytest.mark.parametrize(
    "fragment",
    [
        ".globl  _main",
        "_main:",
        "_plus:",
        "_dot:",
        "_emit:",
        "_cr:",
        "_print_str:",
        "Lfmt_dot:",
        "Ldstack_base",
    ],
)
def test_runtime_sections_present(fragment):
    asm = _emit_main()
    assert fragment in asm, \
        f"emitted asm should include the runtime fragment {fragment!r}"


def test_emits_program_for_canonical_add():
    asm = _emit_main(Literal(2), Literal(3), PrimRef("+"), PrimRef("."))
    for needle in ("ldr     x0, =2", "ldr     x0, =3", "bl      _plus", "bl      _dot"):
        assert needle in asm, \
            f"canonical add program should contain asm fragment {needle!r}"


def test_main_body_appears_in_definition_order():
    asm = _emit_main(Literal(2), Literal(3), PrimRef("+"))
    two = asm.index("ldr     x0, =2")
    three = asm.index("ldr     x0, =3")
    plus = asm.index("bl      _plus")
    assert two < three < plus, \
        "instructions should appear in source order: 2 then 3 then +"


def test_label_emits_local_assembler_label():
    asm = _emit_main(Label(7))
    assert "L7:" in asm, "Label(7) should emit a Mach-O local label 'L7:'"


def test_unconditional_branch_emits_b():
    asm = _emit_main(Branch(target=3, conditional=False))
    assert "b       L3" in asm, \
        "unconditional Branch should emit 'b L<target>' for the assembler"


def test_conditional_branch_pops_then_cbz():
    asm = _emit_main(Branch(target=2, conditional=True))
    assert "ldr     x0, [x19], #8" in asm, \
        "conditional Branch should pop TOS into x0 before testing"
    assert "cbz     x0, L2" in asm, \
        "conditional Branch should branch to its target when popped value is zero"


def test_conditional_branch_emits_pop_before_cbz():
    asm = _emit_main(Branch(target=4, conditional=True))
    pop_idx = asm.index("ldr     x0, [x19], #8")
    cbz_idx = asm.index("cbz     x0, L4")
    assert pop_idx < cbz_idx, "the pop must precede the cbz, not follow it"


def test_if_then_program_round_trip():
    asm = _emit_main(
        Literal(1),
        Branch(target=0, conditional=True),
        Literal(42),
        Label(0),
    )
    pop_idx = asm.index("cbz     x0, L0")
    body_idx = asm.index("ldr     x0, =42")
    label_idx = asm.index("L0:")
    assert pop_idx < body_idx < label_idx, \
        "if/then asm should branch over the body to the label, in that order"


def test_string_lit_emits_print_str_call():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit("hi"))
    assert "adrp    x0, Lstr_0@PAGE" in asm, \
        "StringLit should load address of its interned label via adrp/add"
    assert "add     x0, x0, Lstr_0@PAGEOFF" in asm, \
        "StringLit should complete the address with PAGEOFF"
    assert "mov     x1, #2" in asm, \
        "StringLit should pass byte length in x1 (len('hi') == 2)"
    assert "bl      _print_str" in asm, \
        "StringLit should call into the runtime _print_str helper"


def test_each_string_lit_gets_a_fresh_label():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit("a"), StringLit("b"))
    assert "Lstr_0:" in asm and "Lstr_1:" in asm, \
        "consecutive StringLits should each get a unique Lstr_N label"


def test_string_content_interned_in_cstring_section():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit("hi"))
    cstring_idx = asm.rfind(".section __TEXT,__cstring")
    label_idx = asm.rfind("Lstr_0:")
    asciz_idx = asm.rfind('.asciz  "hi"')
    assert cstring_idx != -1, \
        "asm should declare a __TEXT,__cstring section to hold user strings"
    assert label_idx > cstring_idx, "Lstr_0: must be inside the cstring section"
    assert asciz_idx > label_idx, ".asciz directive must follow the label"


def test_each_string_lit_is_nul_terminated():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit("Hello, "), StringLit("mzt"), StringLit("!"))
    user_string_asciz = sum(
        1 for line in asm.splitlines() if line.lstrip().startswith(".asciz")
    )
    assert user_string_asciz == 4, \
        "every interned user string plus the runtime printf format must use .asciz: " \
        "without the trailing NUL the __TEXT,__cstring linker collapses adjacent " \
        "strings into one and remaps later Lstr_N labels to the start of the merged blob"
    user_string_section_idx = asm.find("Lstr_0:")
    user_strings = asm[user_string_section_idx:]
    assert ".ascii " not in user_strings, \
        "user-string section must not contain .ascii (no NUL) — only .asciz"


def test_string_with_special_chars_is_escaped():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit('say "hi"\nthere'))
    assert r'\042' in asm or r'\"' in asm, \
        "double quote in content must be escaped so the assembler does not close the string early"
    assert r"\012" in asm, \
        "newline in content must be escaped as octal so the assembler emits a 0x0a byte"


def test_byte_length_uses_utf8_byte_count():
    from mzt.ir import StringLit
    asm = _emit_main(StringLit("é"))
    assert "mov     x1, #2" in asm, \
        "string length should be UTF-8 byte length, not Python char count"


def test_inline_primitive_does_not_emit_bl():
    asm = _emit_main(PrimRef("zero"))
    assert "bl      _zero" not in asm, \
        "an inline primitive must be expanded at the call site, not invoked via bl"
    assert "str     xzr, [x19, #-8]!" in asm, \
        "PrimRef('zero') should inline its body (str xzr push) directly"


def test_runtime_does_not_define_inline_primitive_function():
    asm = _emit_main()
    assert "_zero:" not in asm, \
        "inline primitives have no callers via bl; the runtime must not waste " \
        "bytes emitting _zero: as a callable function"


def test_non_inline_primitives_still_emit_bl():
    asm = _emit_main(PrimRef("dup"))
    assert "bl      _dup" in asm, \
        "non-inline primitives must still be invoked via bl"


def test_addr_loads_user_mem_base_and_pushes():
    from mzt.ir import Addr
    asm = _emit_main(Addr(0))
    assert "adrp    x0, Luser_mem@PAGE" in asm, \
        "Addr should load user-memory base via adrp/PAGE"
    assert "add     x0, x0, Luser_mem@PAGEOFF" in asm, \
        "Addr should complete the address with PAGEOFF"
    assert "str     x0, [x19, #-8]!" in asm, \
        "Addr should push the computed address onto the data stack"


def test_addr_with_zero_offset_omits_add_immediate():
    from mzt.ir import Addr
    asm = _emit_main(Addr(0))
    assert "add     x0, x0, #0" not in asm, \
        "Addr(0) should not emit a redundant 'add x0, x0, #0' instruction"


def test_addr_with_nonzero_offset_includes_add_immediate():
    from mzt.ir import Addr
    asm = _emit_main(Addr(32))
    assert "add     x0, x0, #32" in asm, \
        "Addr(32) should emit 'add x0, x0, #32' to advance from the base"


def test_runtime_emits_user_mem_zerofill():
    asm = emit_program([ColonDef("main", ())], user_memory_bytes=64)
    assert ".zerofill __DATA,__bss,Luser_mem,64,3" in asm, \
        "runtime epilogue should declare a 64-byte Luser_mem .zerofill block"


def test_runtime_user_mem_minimum_size():
    asm = emit_program([ColonDef("main", ())], user_memory_bytes=0)
    assert ".zerofill __DATA,__bss,Luser_mem,16,3" in asm, \
        "Luser_mem block should default to 16 bytes when no variables are declared"


def test_runtime_user_mem_rounded_up_to_16():
    asm = emit_program([ColonDef("main", ())], user_memory_bytes=33)
    assert ".zerofill __DATA,__bss,Luser_mem,48,3" in asm, \
        "Luser_mem block should be rounded up to a 16-byte boundary"


def test_hyphenated_word_name_produces_legal_asm_label():
    asm = emit_program([ColonDef("paint-row", (Literal(1),))])
    assert "_word_paint-row:" not in asm, \
        "raw hyphen in label name produces clang 'unexpected token' (parsed as subtraction)"
    assert "_word_paint_row:" in asm, \
        "hyphens in Forth names must be sanitized to underscores in asm labels"


def test_hyphenated_colon_ref_uses_sanitized_label():
    defs = [
        ColonDef("paint-row", (Literal(1),)),
        ColonDef("main", (ColonRef("paint-row"),)),
    ]
    asm = emit_program(defs)
    assert "bl      _word_paint_row" in asm, \
        "ColonRef to a hyphenated name must call its sanitized label"
    assert "bl      _word_paint-row" not in asm, \
        "the raw hyphenated form must not appear in any bl"


def test_definition_and_reference_labels_round_trip():
    defs = [
        ColonDef("a-b-c", (Literal(0),)),
        ColonDef("main",  (ColonRef("a-b-c"),)),
    ]
    asm = emit_program(defs)
    label_def = "_word_a_b_c:"
    label_ref = "bl      _word_a_b_c"
    assert label_def in asm and label_ref in asm, \
        "every hyphen in the source name maps to underscore in BOTH the label " \
        "definition and its references; otherwise the linker can't resolve"


def test_sanitization_collision_is_detected():
    defs = [
        ColonDef("a-b", (Literal(1),)),
        ColonDef("a_b", (Literal(2),)),
    ]
    with pytest.raises(ValueError, match="sanitiz"):
        emit_program(defs)
