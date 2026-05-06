from pathlib import Path

import pytest

from mzt.compiler import compile_source
from mzt.ir import ColonDef
from mzt.tokenizer import tokenize


def _find(defs: list[ColonDef], name: str) -> ColonDef:
    found = next((d for d in defs if d.name == name), None)
    assert found is not None, f"expected def {name!r} in {[d.name for d in defs]}"
    return found


# ---------------------------------------------------------------------------
# Tokenizer-level: every token carries (start_offset, end_offset)
# ---------------------------------------------------------------------------

def test_token_carries_start_and_end_offsets():
    [tok] = tokenize("dup")
    assert tok.start_offset == 0, \
        "first char of 'dup' is at offset 0"
    assert tok.end_offset == 3, \
        "'dup' spans offsets 0..3 exclusive"


def test_adjacent_word_tokens_have_consistent_offsets():
    tokens = tokenize("dup drop")
    assert (tokens[0].start_offset, tokens[0].end_offset) == (0, 3), \
        "first token 'dup' should span 0..3"
    assert (tokens[1].start_offset, tokens[1].end_offset) == (4, 8), \
        "second token 'drop' should span 4..8 (one space between them)"


@pytest.mark.parametrize(
    "text",
    [
        "dup",
        "  dup\n   drop",
        ": foo dup * ;",
        "42 constant max",
        "create bar 16 allot",
        "synonym d dup",
    ],
    ids=["bare", "leading-and-newline", "colon-def", "constant",
         "create-allot", "synonym"],
)
def test_token_offsets_round_trip_to_original_text(text):
    tokens = tokenize(text)
    for t in tokens:
        sliced = text[t.start_offset:t.end_offset]
        assert sliced == t.raw, \
            f"text[{t.start_offset}:{t.end_offset}] = {sliced!r} should equal raw {t.raw!r}"


def test_string_token_offsets_include_the_dot_quote_framing():
    text = '."  hi "'
    [tok] = tokenize(text)
    assert text[tok.start_offset:tok.end_offset] == text, \
        "string-literal span should cover .\" prefix and closing quote, not just content"


# ---------------------------------------------------------------------------
# Per-definition capture on ColonDef.source_text
# ---------------------------------------------------------------------------

def test_colon_def_captures_full_source_text():
    src = ": foo dup * ;"
    [d] = compile_source(src)
    assert d.source_text == ": foo dup * ;", \
        f"colon def source_text should be the verbatim '{src}'; got {d.source_text!r}"


def test_colon_def_capture_preserves_inline_paren_comment():
    src = ": foo ( a -- b ) dup * ;"
    [d] = compile_source(src)
    assert d.source_text == src, \
        f"paren stack-effect comment must survive verbatim in source_text; got {d.source_text!r}"


def test_colon_def_capture_preserves_line_comment_and_newline():
    src = ": foo \\ doubles\n  dup * ;"
    [d] = compile_source(src)
    assert d.source_text == src, \
        f"backslash line comments and the newlines they require must round-trip; got {d.source_text!r}"


def test_synonym_captures_keyword_through_target():
    defs = compile_source("synonym d dup : main d ;")
    syn = _find(defs, "d")
    assert syn.source_text == "synonym d dup", \
        f"synonym capture should be 'synonym d dup', not just part of it; got {syn.source_text!r}"


def test_constant_captures_value_through_name():
    src = "42 constant max : main max ;"
    defs = compile_source(src)
    max_def = _find(defs, "max")
    assert max_def.source_text == "42 constant max", \
        f"constant capture should start at the literal, not at 'constant'; got {max_def.source_text!r}"


def test_variable_captures_keyword_and_name():
    src = "variable foo : main foo ;"
    defs = compile_source(src)
    foo = _find(defs, "foo")
    assert foo.source_text == "variable foo", \
        f"variable capture should be 'variable foo'; got {foo.source_text!r}"


def test_create_without_allot_captures_keyword_and_name():
    src = "create bar : main bar ;"
    defs = compile_source(src)
    bar = _find(defs, "bar")
    assert bar.source_text == "create bar", \
        f"create without allot should capture 'create bar'; got {bar.source_text!r}"


def test_create_with_allot_captures_through_allot_keyword():
    src = "create bar 16 allot : main bar ;"
    defs = compile_source(src)
    bar = _find(defs, "bar")
    assert bar.source_text == "create bar 16 allot", \
        f"create with allot should capture full 'create bar 16 allot'; got {bar.source_text!r}"


def test_create_with_multiple_allot_pairs_captures_through_last():
    src = "create bar 8 allot 16 allot : main bar ;"
    defs = compile_source(src)
    bar = _find(defs, "bar")
    assert bar.source_text == "create bar 8 allot 16 allot", \
        f"create with multiple allot pairs should capture all of them; got {bar.source_text!r}"


# ---------------------------------------------------------------------------
# Round-trip property — re-compile captured span yields equivalent IR
# ---------------------------------------------------------------------------

def test_self_contained_colon_def_round_trips_to_identical_ir():
    [original] = compile_source(": foo dup * ;")
    [redone] = compile_source(original.source_text)
    assert original.body == redone.body, \
        "captured source text must re-compile to identical IR body"
    assert original.name == redone.name, \
        "captured source text must re-compile under the same name"


@pytest.mark.parametrize(
    "src",
    [
        ": foo dup * ;",
        ": id ;",
        ": maybe-zero if drop 0 then ;",
        ": loop10 0 begin dup 10 < while 1+ repeat ;",
        ": doit 1 2 + . ;",
    ],
    ids=["square-of", "nullary", "if-then", "begin-while", "literals-and-emit"],
)
def test_a_zoo_of_self_contained_colon_defs_round_trip(src):
    [original] = compile_source(src)
    [redone] = compile_source(original.source_text)
    assert original.body == redone.body, \
        f"{src!r} should re-compile from its captured source to identical IR"


# ---------------------------------------------------------------------------
# Include: definitions sourced from a file carry their span from that file
# ---------------------------------------------------------------------------

def test_def_from_included_file_carries_source_text_from_that_file(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": dbl 2 * ;\n")
    main = tmp_path / "main.fs"
    main.write_text("include helper.fs : main 5 dbl ;")
    defs = compile_source(main.read_text(), source_path=main)
    dbl = _find(defs, "dbl")
    assert dbl.source_text == ": dbl 2 * ;", \
        f"def from included file should carry that file's exact span; got {dbl.source_text!r}"


def test_synonym_in_included_file_round_trips_via_capture(tmp_path: Path):
    lib = tmp_path / "lib.fs"
    lib.write_text(": dbl 2 * ;\nsynonym double dbl\n")
    main = tmp_path / "main.fs"
    main.write_text("include lib.fs : main 7 double ;")
    defs = compile_source(main.read_text(), source_path=main)
    syn = _find(defs, "double")
    assert syn.source_text == "synonym double dbl", \
        f"synonym from included file should carry its single-line source span; got {syn.source_text!r}"


def test_two_defs_on_one_line_capture_independent_spans():
    src = ": foo 1 ; : bar 2 ;"
    defs = compile_source(src)
    foo = _find(defs, "foo")
    bar = _find(defs, "bar")
    assert foo.source_text == ": foo 1 ;", \
        f"first def on a multi-def line should capture only its own span; got {foo.source_text!r}"
    assert bar.source_text == ": bar 2 ;", \
        f"second def should capture only its own span; got {bar.source_text!r}"


def test_primitives_are_not_in_the_returned_def_list():
    """Sanity check: primitives never appear as ColonDefs, so they
    have no source_text — nothing to capture, nothing to save."""
    defs = compile_source(": main dup drop ;")
    names = {d.name for d in defs}
    assert "dup" not in names and "drop" not in names, \
        "primitives are not represented as ColonDefs and don't need source_text"
