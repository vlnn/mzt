import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import Addr, ColonDef, ColonRef, Literal, PrimRef


def test_variable_creates_a_colon_word():
    defs = compile_source("variable foo")
    assert len(defs) == 1, "'variable foo' should produce exactly one definition"
    assert defs[0].name == "foo", \
        "variable should bind the name to a callable colon word"


def test_variable_body_pushes_an_address():
    [d] = compile_source("variable foo")
    assert len(d.body) == 1, \
        "variable body should be a single address-pushing cell"
    assert isinstance(d.body[0], Addr), \
        "variable body should be a single Addr cell"


def test_first_variable_starts_at_offset_zero():
    [d] = compile_source("variable foo")
    [cell] = d.body
    assert cell.offset == 0, \
        "first user variable should claim offset 0 in the user-memory block"


def test_subsequent_variables_advance_by_cell_size():
    defs = compile_source("variable a variable b variable c")
    offsets = [d.body[0].offset for d in defs]
    assert offsets == [0, 8, 16], \
        "each variable should reserve one 8-byte cell so offsets advance by 8"


def test_create_without_allot_reserves_no_bytes():
    defs = compile_source("create a create b")
    [a, b] = defs
    assert a.body[0].offset == 0, "first create should land at offset 0"
    assert b.body[0].offset == 0, \
        "create with no allot should reserve zero bytes — second create lands on top"


def test_create_with_allot_advances_bump_pointer():
    defs = compile_source("create a 100 allot create b")
    a_off = defs[0].body[0].offset
    b_off = defs[1].body[0].offset
    assert a_off == 0, "first create starts at offset 0"
    assert b_off == 100, \
        "100 allot after create should push the bump pointer by 100"


def test_variable_after_create_with_allot():
    defs = compile_source("create buf 32 allot variable v")
    assert defs[0].body[0].offset == 0, \
        "create at the start lands at offset 0"
    assert defs[1].body[0].offset == 32, \
        "variable following 'create buf 32 allot' should land at offset 32"


def test_allot_with_zero_is_a_noop():
    defs = compile_source("create a 0 allot create b")
    assert defs[0].body[0].offset == 0
    assert defs[1].body[0].offset == 0, \
        "0 allot should not advance the bump pointer"


@pytest.mark.parametrize(
    "source,fragment",
    [
        ("variable",                    "must be followed by a name"),
        ("create",                      "must be followed by a name"),
        ("allot",                       "without a preceding"),
        ("variable foo allot",          "without a preceding"),
        ("create foo allot",            "without a preceding"),
        ("create foo dup allot",        "must be a positive integer"),
        ("create foo -5 allot",         "must be a positive integer"),
    ],
)
def test_malformed_memory_definitions_raise(source, fragment):
    with pytest.raises(CompileError, match=fragment):
        compile_source(source)


def test_variable_can_be_referenced_inside_colon_body():
    defs = compile_source("variable v : main v . ;")
    main_body = defs[1].body
    refs = [c for c in main_body if isinstance(c, ColonRef)]
    assert any(r.name == "v" for r in refs), \
        "a colon body referencing a variable should resolve it as a ColonRef"


def test_memory_words_cannot_overlap_primitives():
    with pytest.raises(CompileError, match="primitive"):
        compile_source("variable dup")


def test_memory_words_cannot_overlap_control_flow():
    with pytest.raises(CompileError, match="control-flow"):
        compile_source("variable if")


def test_memory_words_cannot_redefine_each_other():
    with pytest.raises(CompileError, match="already defined"):
        compile_source("variable foo variable foo")
