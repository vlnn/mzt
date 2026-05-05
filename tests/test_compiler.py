import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import Branch, ColonDef, ColonRef, Label, Literal, PrimRef


def test_empty_source_yields_no_definitions():
    assert compile_source("") == [], \
        "empty source should produce zero colon definitions"


def test_compiles_canonical_main():
    [d] = compile_source(": main 2 3 + . ;")
    assert d.name == "main", "colon definition's name should match the source word"
    assert d.body == (Literal(2), Literal(3), PrimRef("+"), PrimRef(".")), \
        "': main 2 3 + . ;' should compile to two literals followed by + and ."


@pytest.mark.parametrize(
    "source,expected_value",
    [
        (": main 0 ;", 0),
        (": main 42 ;", 42),
        (": main -7 ;", -7),
    ],
)
def test_literal_values_pass_through(source, expected_value):
    [d] = compile_source(source)
    assert d.body == (Literal(expected_value),), \
        f"literal {expected_value} should appear unchanged in the IR"


def test_unknown_word_becomes_colon_ref():
    [d] = compile_source(": main square ;")
    assert d.body == (ColonRef("square"),), \
        "non-primitive words should resolve to ColonRef for later linking"


def test_known_primitive_becomes_prim_ref():
    [d] = compile_source(": main + ;")
    assert d.body == (PrimRef("+"),), \
        "registered primitive words should resolve to PrimRef"


def test_multiple_colon_definitions_in_source_order():
    defs = compile_source(": helper 1 ; : main helper . ;")
    assert [d.name for d in defs] == ["helper", "main"], \
        "definitions should be returned in source order"
    assert defs[1].body == (ColonRef("helper"), PrimRef(".")), \
        "main should reference helper as ColonRef and . as PrimRef"


def test_paren_comments_inside_body_are_ignored():
    [d] = compile_source(": main 2 ( push two ) 3 ( push three ) + . ;")
    assert d.body == (Literal(2), Literal(3), PrimRef("+"), PrimRef(".")), \
        "comments inside a colon body should not appear in the IR"


@pytest.mark.parametrize(
    "source,error_fragment",
    [
        (": ;", "must be followed by a word name"),
        (":", "must be followed by a word name"),
        (": main 2 3 +", "missing closing"),
        ("2 3 + . ;", "expected ':'"),
        ("; : main 1 ;", "expected ':'"),
    ],
)
def test_compile_errors(source, error_fragment):
    with pytest.raises(CompileError, match=error_fragment):
        compile_source(source)


def _body(source: str):
    [d] = compile_source(source)
    return d.body


def test_if_then_emits_conditional_branch_and_label():
    body = _body(": main 1 if 42 then ;")
    assert body == (
        Literal(1),
        Branch(target=0, conditional=True),
        Literal(42),
        Label(0),
    ), "if/then should compile to conditional branch past the body and a label"


def test_if_else_then_emits_orig_pair_with_unconditional_skip():
    body = _body(": main 1 if 11 else 22 then ;")
    assert body == (
        Literal(1),
        Branch(target=0, conditional=True),
        Literal(11),
        Branch(target=1, conditional=False),
        Label(0),
        Literal(22),
        Label(1),
    ), "if/else/then should generate two labels: else landing and post-then"


def test_begin_until_emits_back_branch():
    body = _body(": main begin 1 until ;")
    assert body == (
        Label(0),
        Literal(1),
        Branch(target=0, conditional=True),
    ), "begin/until should mark a back-jump target and emit a conditional branch to it"


def test_begin_again_emits_unconditional_back_branch():
    body = _body(": main begin 1 again ;")
    assert body == (
        Label(0),
        Literal(1),
        Branch(target=0, conditional=False),
    ), "begin/again should mark a back-jump target and branch unconditionally"


def test_begin_while_repeat_emits_test_and_back_branch():
    body = _body(": main begin 1 while 2 repeat ;")
    assert body == (
        Label(0),
        Literal(1),
        Branch(target=1, conditional=True),
        Literal(2),
        Branch(target=0, conditional=False),
        Label(1),
    ), "begin/while/repeat should test, branch out of loop on false, branch back on true"


def test_nested_if_else_get_distinct_labels():
    body = _body(": main 1 if 2 if 3 else 4 then else 5 then ;")
    assert body == (
        Literal(1),
        Branch(target=0, conditional=True),
        Literal(2),
        Branch(target=1, conditional=True),
        Literal(3),
        Branch(target=2, conditional=False),
        Label(1),
        Literal(4),
        Label(2),
        Branch(target=3, conditional=False),
        Label(0),
        Literal(5),
        Label(3),
    ), "nested if/else/then chains should each get fresh, non-colliding label IDs"


def test_label_ids_are_unique_across_definitions():
    defs = compile_source(": a 1 if 2 then ; : b 3 if 4 then ;")
    body_a = defs[0].body
    body_b = defs[1].body
    used_in_a = {c.id for c in body_a if isinstance(c, Label)}
    used_in_b = {c.id for c in body_b if isinstance(c, Label)}
    assert used_in_a.isdisjoint(used_in_b), \
        "label IDs must be globally unique so emitted Mach-O labels never collide"


@pytest.mark.parametrize(
    "source,fragment",
    [
        (": main then ;",            "without matching"),
        (": main else ;",            "without matching"),
        (": main if 1 ;",            "unclosed control flow"),
        (": main begin 1 ;",         "unclosed control flow"),
        (": main begin while 1 ;",   "unclosed control flow"),
        (": main repeat ;",          "without matching"),
        (": main while ;",           "without matching"),
        (": main until ;",           "without matching"),
        (": main again ;",           "without matching"),
        (": main if 1 repeat ;",     "without matching"),
    ],
)
def test_malformed_control_flow_raises(source, fragment):
    with pytest.raises(CompileError, match=fragment):
        compile_source(source)


@pytest.mark.parametrize("name", ["if", "then", "else", "begin", "until", "again", "while", "repeat"])
def test_control_words_cannot_name_a_colon_definition(name):
    with pytest.raises(CompileError, match="control-flow"):
        compile_source(f": {name} 1 ;")


def test_string_token_compiles_to_string_lit():
    from mzt.ir import StringLit
    [d] = compile_source(': main ." Hello!" ;')
    assert d.body == (StringLit("Hello!"),), \
        "STRING tokens should compile to StringLit cells with the content preserved"


def test_string_alongside_other_cells():
    from mzt.ir import StringLit
    [d] = compile_source(': main ." hi" cr ;')
    assert d.body == (StringLit("hi"), PrimRef("cr")), \
        "string and following words should appear in source order in the IR"


def test_multiple_strings_each_become_string_lit():
    from mzt.ir import StringLit
    [d] = compile_source(': main ." one" ." two" ;')
    assert d.body == (StringLit("one"), StringLit("two")), \
        "multiple strings should each yield their own StringLit cell"
