import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import ColonDef, Literal


def test_constant_compiles_to_colon_def_with_single_literal():
    [c] = compile_source("100 constant max-items")
    assert isinstance(c, ColonDef), \
        "constant should produce a ColonDef like variable does"
    assert c.name == "max-items", \
        f"constant should name the definition 'max-items'; got {c.name!r}"
    assert c.body == (Literal(100),), \
        f"constant body should be exactly one Literal cell; got {c.body!r}"


@pytest.mark.parametrize("value", [0, 1, 42, -1, -42, 1_000_000_000_000])
def test_constant_carries_signed_integer_values(value):
    [c] = compile_source(f"{value} constant n")
    assert c.body == (Literal(value),), \
        f"constant n with value {value} should compile to body (Literal({value}),)"


def test_constant_can_be_used_inside_colon_body():
    src = "42 constant ANSWER : main ANSWER . ;"
    defs = compile_source(src)
    answer = next(d for d in defs if d.name == "ANSWER")
    main = next(d for d in defs if d.name == "main")
    assert answer.body == (Literal(42),), \
        "ANSWER constant should compile as a one-cell colon definition with Literal(42)"
    from mzt.ir import ColonRef
    assert ColonRef("ANSWER") in main.body, \
        "main should resolve ANSWER to a ColonRef (it's now a colon-definable name)"


def test_constant_without_preceding_number_raises():
    with pytest.raises(CompileError, match="constant"):
        compile_source("constant orphan")


def test_constant_without_following_name_raises():
    with pytest.raises(CompileError, match="constant"):
        compile_source("100 constant")


def test_constant_redefining_existing_name_raises():
    with pytest.raises(CompileError, match="already defined"):
        compile_source("1 constant foo  2 constant foo")


def test_constant_using_primitive_name_raises():
    with pytest.raises(CompileError, match="primitive"):
        compile_source("100 constant +")


def test_stray_number_at_top_level_without_constant_still_raises():
    with pytest.raises(CompileError, match="100"):
        compile_source("100")


def test_two_constants_in_one_program_compile_independently():
    defs = compile_source("10 constant ten  20 constant twenty")
    assert len(defs) == 2, \
        f"two constants should produce two ColonDefs; got {len(defs)}"
    by_name = {d.name: d for d in defs}
    assert by_name["ten"].body == (Literal(10),), \
        "first constant 'ten' should carry Literal(10)"
    assert by_name["twenty"].body == (Literal(20),), \
        "second constant 'twenty' should carry Literal(20)"
