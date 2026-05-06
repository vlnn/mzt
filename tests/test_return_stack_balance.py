import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import PrimRef


def test_balanced_to_r_then_r_from_compiles():
    [d] = compile_source(": main 5 >r r> ;")
    assert d.body == (
        # Literal(5) is the only data cell, then >r and r>
        d.body[0],
        PrimRef(">r"),
        PrimRef("r>"),
    ), ">r followed by r> should compile body verbatim — sanity check on the IR shape"


def test_unmatched_to_r_at_end_of_definition_raises():
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": main 5 >r ;")


def test_lone_r_from_underflows_compile_time_check():
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": main r> ;")


def test_r_fetch_with_empty_return_stack_raises():
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": main r@ ;")


def test_r_fetch_with_one_item_on_return_stack_compiles():
    [d] = compile_source(": main 5 >r r@ drop r> drop ;")
    assert any(isinstance(c, PrimRef) and c.name == "r@" for c in d.body), \
        "r@ should appear in the compiled body when return stack has one item"


def test_two_to_r_two_r_from_balances():
    [d] = compile_source(": main 1 2 >r >r r> r> ;")
    names = [c.name for c in d.body if isinstance(c, PrimRef)]
    assert names == [">r", ">r", "r>", "r>"], \
        f"two >r and two r> should remain in the body in source order; got {names}"


def test_imbalance_across_distinct_definitions_is_isolated():
    defs = compile_source(": helper 5 >r r> ; : main helper ;")
    assert [d.name for d in defs] == ["helper", "main"], \
        "balanced helper followed by main should both compile cleanly"


def test_imbalance_in_helper_only_blames_helper():
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": helper 5 >r ; : main helper ;")


def test_r_depth_resets_between_definitions():
    [_, _] = compile_source(": a 5 >r r> ; : b 7 >r r> ;")


@pytest.mark.parametrize(
    "source",
    [
        ": main 5 >r ;",
        ": main r> ;",
        ": main r@ ;",
        ": main 5 >r r> r> ;",
        ": main 5 >r >r r> ;",
    ],
)
def test_known_imbalances_all_raise(source):
    with pytest.raises(CompileError, match="return stack"):
        compile_source(source)


def test_error_message_names_the_definition():
    with pytest.raises(CompileError, match="main"):
        compile_source(": main 5 >r ;")
