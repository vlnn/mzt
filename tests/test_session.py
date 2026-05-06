from pathlib import Path

import pytest

from mzt.compiler import compile_increment
from mzt.session import Session, save_session, save_word


def _read(path: Path) -> str:
    return path.read_text()


# ---------------------------------------------------------------------------
# Session basics
# ---------------------------------------------------------------------------

def test_session_starts_empty():
    s = Session()
    assert list(s.interactive_defs()) == [], \
        "fresh session has no interactive defs"
    assert s.include_lines == [], \
        "fresh session has no include lines logged"


def test_session_feed_adds_inline_def_to_interactive_history():
    s = Session()
    s.feed(": foo 1 ;")
    interactive_names = [d.name for d in s.interactive_defs()]
    assert interactive_names == ["foo"], \
        f"foo should be in interactive history; got {interactive_names!r}"


def test_session_feed_records_include_line_separately(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 1 ;")
    s = Session(include_dirs=[tmp_path])
    s.feed("include helper.fs")
    assert s.include_lines == ["include helper.fs"], \
        f"include line should be logged verbatim; got {s.include_lines!r}"
    interactive_names = [d.name for d in s.interactive_defs()]
    assert "helped" not in interactive_names, \
        "defs imported via include must NOT be classified as interactive"


def test_session_feed_with_mixed_input_separates_correctly(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 1 ;")
    s = Session(include_dirs=[tmp_path])
    s.feed("include helper.fs : foo helped ;")
    assert s.include_lines == ["include helper.fs"], \
        "include line should be logged once"
    interactive_names = [d.name for d in s.interactive_defs()]
    assert interactive_names == ["foo"], \
        f"only foo (typed inline) should be in interactive history; got {interactive_names!r}"


def test_session_feed_redefinition_replaces_prior_interactive_entry():
    s = Session()
    s.feed(": foo 1 ;")
    s.feed(": foo 2 ;")
    interactive = list(s.interactive_defs())
    assert len(interactive) == 1, \
        f"after redefinition there should be one entry; got {[d.name for d in interactive]}"
    assert interactive[0].source_text == ": foo 2 ;", \
        f"interactive entry should be the latest source_text; got {interactive[0].source_text!r}"


def test_session_uses_permissive_redefinition_by_default():
    s = Session()
    s.feed(": foo 1 ;")
    s.feed(": foo 2 ;")
    assert any("foo" in w for w in s.state.warnings), \
        "session must enable allow_redefinition so REPL workflow doesn't error"


# ---------------------------------------------------------------------------
# save_word — write a single binding to a file
# ---------------------------------------------------------------------------

def test_save_word_writes_source_text_for_inline_def(tmp_path: Path):
    s = Session()
    s.feed(": foo dup * ;")
    out = tmp_path / "foo.fs"
    save_word(s, "foo", out)
    assert _read(out) == ": foo dup * ;\n", \
        f"saved file should be the verbatim source plus trailing newline; got {_read(out)!r}"


def test_save_word_for_a_synonym_emits_synonym_line(tmp_path: Path):
    s = Session()
    s.feed("synonym d dup")
    out = tmp_path / "d.fs"
    save_word(s, "d", out)
    assert _read(out) == "synonym d dup\n", \
        f"synonym should round-trip as 'synonym d dup'; got {_read(out)!r}"


def test_save_word_for_unknown_name_raises(tmp_path: Path):
    s = Session()
    with pytest.raises(KeyError, match="not-a-word"):
        save_word(s, "not-a-word", tmp_path / "x.fs")


def test_save_word_for_a_primitive_raises(tmp_path: Path):
    s = Session()
    with pytest.raises(ValueError, match="primitive"):
        save_word(s, "dup", tmp_path / "x.fs")


def test_save_word_for_def_from_included_file_uses_that_files_source(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 99 ;\n")
    s = Session(include_dirs=[tmp_path])
    s.feed("include helper.fs")
    out = tmp_path / "out.fs"
    save_word(s, "helped", out)
    assert _read(out) == ": helped 99 ;\n", \
        f"saving an included def should emit its verbatim source; got {_read(out)!r}"


# ---------------------------------------------------------------------------
# save_session — write the full session in definition order
# ---------------------------------------------------------------------------

def test_save_session_includes_then_inline_defs_in_order(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 1 ;\n")
    s = Session(include_dirs=[tmp_path])
    s.feed("include helper.fs")
    s.feed(": foo 2 ;")
    s.feed("synonym sq foo")
    out = tmp_path / "session.fs"
    save_session(s, out)
    text = _read(out)
    expected = "include helper.fs\n\n: foo 2 ;\n\nsynonym sq foo\n"
    assert text == expected, \
        f"session save should emit includes then defs separated by blank lines;\n  expected {expected!r}\n  got      {text!r}"


def test_save_session_preserves_redefinitions_only_as_latest(tmp_path: Path):
    s = Session()
    s.feed(": foo 1 ;")
    s.feed(": foo 2 ;")
    out = tmp_path / "session.fs"
    save_session(s, out)
    text = _read(out)
    assert text.count(": foo") == 1, \
        f"saved session should not contain old versions of foo; got {text!r}"
    assert ": foo 2 ;" in text, \
        f"saved session should contain the latest foo; got {text!r}"


def test_save_session_produces_replayable_file(tmp_path: Path):
    """The round-trip property: feeding the saved file into a fresh Session
    should produce an equivalent dictionary."""
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 1 ;\n")
    s1 = Session(include_dirs=[tmp_path])
    s1.feed("include helper.fs")
    s1.feed(": foo helped ;")
    out = tmp_path / "session.fs"
    save_session(s1, out)

    s2 = Session(include_dirs=[tmp_path])
    s2.feed(out.read_text())
    assert "helped" in s2.state.dictionary, \
        "replayed session should have helped (via include)"
    assert "foo" in s2.state.dictionary, \
        "replayed session should have foo (via inline def)"


def test_save_session_no_includes_no_blank_line_at_top(tmp_path: Path):
    s = Session()
    s.feed(": foo 1 ;")
    out = tmp_path / "session.fs"
    save_session(s, out)
    assert _read(out) == ": foo 1 ;\n", \
        f"session with no includes and one def should be exactly that one def; got {_read(out)!r}"


def test_save_session_dedups_repeated_include_line(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 1 ;\n")
    s = Session(include_dirs=[tmp_path])
    s.feed("include helper.fs")
    s.feed("include helper.fs")  # second time is a no-op
    out = tmp_path / "session.fs"
    save_session(s, out)
    text = _read(out)
    assert text.count("include helper.fs") == 1, \
        f"a re-issued include should appear once in the saved session; got {text!r}"
