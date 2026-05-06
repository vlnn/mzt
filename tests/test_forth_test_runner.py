import textwrap

import pytest

from mzt.forth_test_runner import (
    TEST_WORD_RE,
    discover_test_words,
    synthesize_test_main,
)


def test_discover_returns_test_words_in_source_order():
    src = textwrap.dedent("""
        : test-add  1 2 + 3 assert-eq ;
        : helper  drop ;
        : test-sub  3 1 - 2 assert-eq ;
    """)
    words = discover_test_words(src)
    assert words == ["test-add", "test-sub"], \
        f"discovery should return only test-* words in source order; got {words}"


def test_discover_skips_non_test_definitions():
    src = ": helper 1 ;\n: test-only 42 assert-eq ;"
    assert discover_test_words(src) == ["test-only"], \
        "definitions not starting with 'test-' should not be reported"


def test_discover_handles_empty_source():
    assert discover_test_words("") == [], \
        "empty source should yield no test words"


def test_discover_handles_no_test_words():
    assert discover_test_words(": helper 1 ;\n: other 2 ;") == [], \
        "source without any 'test-*' words should yield empty list"


@pytest.mark.parametrize(
    "name",
    ["test-add", "test-multi-word-name", "test-?dup", "test-1+", "test-foo!"],
)
def test_test_word_re_matches_idiomatic_names(name):
    src = f": {name} 1 2 + 3 assert-eq ;"
    assert discover_test_words(src) == [name], \
        f"discovery should accept the punctuated test name {name!r}"


def test_synthesize_strips_existing_main_and_appends_fresh_one():
    src = textwrap.dedent("""
        : test-foo 1 2 + 3 assert-eq ;
        : main test-foo test-bar ;
    """).strip()
    out = synthesize_test_main(src, "test-foo")
    assert "test-foo test-bar" not in out, \
        "the original multi-call main should be stripped from the synthesized program"
    assert out.rstrip().endswith(": main test-foo ;"), \
        f"synthesized program should end with ': main test-foo ;'; got {out!r}"


def test_synthesize_works_when_no_main_present():
    src = ": test-foo 1 1 assert-eq ;"
    out = synthesize_test_main(src, "test-foo")
    assert ": test-foo" in out, \
        "test-foo definition should still be present in the synthesized output"
    assert out.rstrip().endswith(": main test-foo ;"), \
        "a fresh main should be appended even when none was present originally"


def test_synthesize_keeps_includes_intact():
    src = textwrap.dedent("""
        include test-lib.fs

        : test-add 1 2 + 3 assert-eq ;
        : main test-add ;
    """).strip()
    out = synthesize_test_main(src, "test-add")
    assert "include test-lib.fs" in out, \
        "include directives must survive main rewriting — they bring in assert-eq"


def test_synthesize_strips_main_with_multi_line_body():
    src = textwrap.dedent("""
        : test-foo 1 1 assert-eq ;
        : test-bar 2 2 assert-eq ;
        : main
            test-foo
            test-bar
        ;
    """).strip()
    out = synthesize_test_main(src, "test-foo")
    # The multi-line main spanning newlines should be stripped — re.DOTALL flag.
    assert "test-foo\n            test-bar" not in out, \
        "multi-line main bodies must be stripped, not just single-line ones"


def test_synthesized_program_compiles():
    """End-to-end compile check on a synthesized test program."""
    from mzt.compiler import compile_source
    src = textwrap.dedent("""
        : test-arithmetic 2 3 + 5 = if else 1 then ;
        : main test-arithmetic ;
    """).strip()
    out = synthesize_test_main(src, "test-arithmetic")
    defs = compile_source(out)
    names = {d.name for d in defs}
    assert "test-arithmetic" in names and "main" in names, \
        f"synthesized program should compile to both test-arithmetic and a main; got {names}"
