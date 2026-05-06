import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import ColonDef, ColonRef, Literal, PrimRef, WordAddr


def test_word_addr_ir_exists_and_is_frozen_hashable():
    a = WordAddr("foo")
    b = WordAddr("foo")
    assert a == b, "WordAddr should compare by name"
    assert hash(a) == hash(b), "WordAddr should be hashable for set/dict use"


def test_noname_inside_colon_emits_word_addr_to_synthetic_definition():
    defs = compile_source(": main :noname 42 ; ;")
    main = next(d for d in defs if d.name == "main")
    word_addrs = [c for c in main.body if isinstance(c, WordAddr)]
    assert len(word_addrs) == 1, \
        f"main should have exactly one WordAddr (the noname address); got body {main.body!r}"


def test_noname_generates_a_synthetic_top_level_def():
    defs = compile_source(": main :noname 42 ; ;")
    synthetic = [d for d in defs if d.name != "main"]
    assert len(synthetic) == 1, \
        f"compiling ': main :noname 42 ; ;' should yield one synthetic def besides main; got {[d.name for d in defs]}"
    assert synthetic[0].body == (Literal(42),), \
        f"synthetic noname's body should be exactly Literal(42); got {synthetic[0].body!r}"


def test_word_addr_in_main_targets_the_synthetic_def_name():
    defs = compile_source(": main :noname 42 ; ;")
    main = next(d for d in defs if d.name == "main")
    synthetic = next(d for d in defs if d.name != "main")
    word_addrs = [c for c in main.body if isinstance(c, WordAddr)]
    assert word_addrs[0].name == synthetic.name, \
        f"the WordAddr in main should target the synthetic noname's name; " \
        f"WordAddr={word_addrs[0].name!r}, synthetic={synthetic.name!r}"


def test_noname_synthetic_names_are_distinct_across_multiple_uses():
    defs = compile_source(": main :noname 1 ; :noname 2 ; ;")
    synthetic_names = [d.name for d in defs if d.name != "main"]
    assert len(synthetic_names) == 2, \
        f"two :noname uses should produce two synthetic defs; got {synthetic_names}"
    assert len(set(synthetic_names)) == 2, \
        f"synthetic noname names must be unique; got {synthetic_names}"


def test_noname_body_can_contain_arbitrary_words():
    defs = compile_source(": main :noname 1 2 + ; ;")
    synthetic = next(d for d in defs if d.name != "main")
    assert Literal(1) in synthetic.body
    assert Literal(2) in synthetic.body
    assert PrimRef("+") in synthetic.body, \
        "noname body should contain primitive references just like a regular colon body"


def test_noname_can_use_recurse_to_self():
    defs = compile_source(": main :noname dup 1 < if drop 1 else dup 1 - recurse * then ; ;")
    synthetic = next(d for d in defs if d.name != "main")
    assert any(
        isinstance(c, ColonRef) and c.name == synthetic.name
        for c in synthetic.body
    ), "recurse inside a :noname body should resolve to the synthetic noname's name"


def test_noname_at_top_level_raises():
    # :noname only makes sense inside a colon body — at top level there's
    # no surrounding stack to push the address onto.
    with pytest.raises(CompileError, match="noname"):
        compile_source(":noname 42 ;")


def test_noname_without_closing_semicolon_raises():
    with pytest.raises(CompileError):
        compile_source(": main :noname 42 ;")  # missing the outer ;


def test_noname_with_unmatched_if_inside_raises():
    with pytest.raises(CompileError):
        compile_source(": main :noname if ; ;")  # unclosed if inside noname


def test_two_noname_followed_by_execute():
    # The pattern: define a thunk, immediately execute it. xt machinery roundtrip.
    defs = compile_source(": main :noname 7 ; execute ;")
    main = next(d for d in defs if d.name == "main")
    word_addr_count = sum(1 for c in main.body if isinstance(c, WordAddr))
    execute_count = sum(1 for c in main.body if isinstance(c, PrimRef) and c.name == "execute")
    assert word_addr_count == 1 and execute_count == 1, \
        f"main should push one WordAddr (the noname's xt) then execute it; got {main.body!r}"
