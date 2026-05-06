from pathlib import Path

import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import ColonDef, ColonRef, Literal, PrimRef


def _find(defs: list[ColonDef], name: str) -> ColonDef | None:
    return next((d for d in defs if d.name == name), None)


def test_synonym_for_primitive_registers_under_new_name():
    defs = compile_source("synonym d dup : main 5 d ;")
    assert _find(defs, "d") is not None, \
        "synonym should register the new name as a defined word"


def test_synonym_for_primitive_body_calls_the_primitive():
    defs = compile_source("synonym d dup : main 5 d ;")
    body = _find(defs, "d").body
    assert body == (PrimRef("dup"),), \
        f"synonym for a primitive should compile to a single PrimRef cell; got {body!r}"


def test_synonym_for_colon_word_body_calls_the_colon_word():
    defs = compile_source(": dbl 2 * ; synonym double dbl : main 5 double ;")
    body = _find(defs, "double").body
    assert body == (ColonRef("dbl"),), \
        f"synonym for a colon word should compile to a single ColonRef cell; got {body!r}"


def test_synonym_referenced_inside_colon_body_resolves_to_a_colon_call():
    defs = compile_source("synonym d dup : main 5 d ;")
    main_body = _find(defs, "main").body
    assert ColonRef("d") in main_body, \
        f"main referencing 'd' should compile to a ColonRef('d'); got {main_body!r}"


def test_synonym_chain_keeps_each_link_separately_dispatched():
    defs = compile_source("synonym a dup synonym b a : main 5 b ;")
    a_body = _find(defs, "a").body
    b_body = _find(defs, "b").body
    assert a_body == (PrimRef("dup"),), \
        "first link in the chain should target the primitive directly"
    assert b_body == (ColonRef("a"),), \
        "second link should target the previous synonym, not flatten to the primitive"


def test_synonym_for_unknown_target_raises_compile_error():
    with pytest.raises(CompileError, match="synonym"):
        compile_source("synonym d not-a-word : main ;")


def test_synonym_redefining_existing_colon_word_raises():
    src = ": foo 1 ; synonym foo dup : main ;"
    with pytest.raises(CompileError, match="already defined"):
        compile_source(src)


def test_synonym_redefining_a_primitive_raises():
    with pytest.raises(CompileError, match="primitive"):
        compile_source("synonym dup drop : main ;")


def test_synonym_redefining_a_control_keyword_raises():
    with pytest.raises(CompileError, match="control-flow"):
        compile_source("synonym if drop : main ;")


def test_synonym_inside_colon_body_raises():
    with pytest.raises(CompileError, match="synonym"):
        compile_source(": main synonym d dup ;")


def test_synonym_without_new_name_raises():
    with pytest.raises(CompileError, match="synonym"):
        compile_source("synonym")


def test_synonym_without_target_raises():
    with pytest.raises(CompileError, match="synonym"):
        compile_source("synonym d")


def test_synonym_target_being_a_number_literal_raises():
    with pytest.raises(CompileError, match="synonym"):
        compile_source("synonym d 42 : main ;")


def test_synonym_carries_through_include(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": dbl 2 * ; synonym double dbl")
    main = tmp_path / "main.fs"
    main.write_text("include helper.fs : main 5 double ;")
    defs = compile_source(main.read_text(), source_path=main)
    names = {d.name for d in defs}
    assert {"dbl", "double", "main"}.issubset(names), \
        f"a synonym defined in an included file should be visible to the includer; got {names}"


def test_synonym_for_constant_pushes_the_constant_value(tmp_path: Path):
    src = "42 constant max : main max ; synonym ceiling max"
    defs = compile_source(src)
    assert _find(defs, "ceiling").body == (ColonRef("max"),), \
        "synonym for a constant should resolve to a ColonRef on the constant's word"


def test_synonym_emits_a_normal_colon_definition_for_the_alias():
    defs = compile_source("synonym d dup : main d ;")
    alias = _find(defs, "d")
    assert isinstance(alias, ColonDef) and len(alias.body) == 1, \
        f"synonym should produce a single-cell ColonDef; got {alias!r}"


@pytest.mark.parametrize(
    "src",
    [
        "synonym",
        "synonym d",
        "synonym d not-a-word : main ;",
        ": main synonym d dup ;",
    ],
    ids=["bare", "no-target", "unknown-target", "inside-body"],
)
def test_synonym_error_paths_all_raise_compile_error(src):
    with pytest.raises(CompileError):
        compile_source(src)
