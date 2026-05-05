import pytest

from mzt.emitter import emit_program
from mzt.ir import ColonDef, ColonRef, Literal, PrimRef


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
