import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import ColonDef, ColonRef, Literal, PrimRef


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
