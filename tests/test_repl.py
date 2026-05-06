from io import StringIO
from pathlib import Path

import pytest

from mzt.repl import Repl, ReplExit, run_line


# A fake "executor": pretend to compile + run a session by recording calls and
# returning a synthetic stdout. Lets us test the shell without clang or arm64.
class FakeExecutor:
    def __init__(self, output: str = "") -> None:
        self.calls: list[str] = []
        self.output = output

    def __call__(self, session, expression: str) -> str:
        self.calls.append(expression)
        return self.output


# ---------------------------------------------------------------------------
# Plain definitions and expressions
# ---------------------------------------------------------------------------

def test_run_line_with_a_colon_def_only_compiles_no_execution():
    repl = Repl(executor=FakeExecutor())
    run_line(repl, ": foo 1 ;")
    assert "foo" in repl.session.state.dictionary, \
        "after a colon def, foo should be in the session dictionary"
    assert repl.executor.calls == [], \
        "a pure colon definition should not trigger any execution"


def test_run_line_with_an_expression_runs_it_via_executor():
    fake = FakeExecutor(output="6\n")
    repl = Repl(executor=fake)
    out = run_line(repl, "1 2 3 + + .")
    assert fake.calls == ["1 2 3 + + ."], \
        f"expression should be passed to executor verbatim; got {fake.calls!r}"
    assert out == "6\n", \
        f"executor output should be returned to the caller; got {out!r}"


def test_run_line_that_mixes_def_and_expression_compiles_def_then_runs_rest():
    fake = FakeExecutor(output="2\n")
    repl = Repl(executor=fake)
    run_line(repl, ": dbl 2 * ; 1 dbl .")
    assert "dbl" in repl.session.state.dictionary, \
        "the colon def part should have been compiled into the session"
    assert fake.calls == ["1 dbl ."], \
        f"the expression part should be sent to the executor without the def; got {fake.calls!r}"


def test_run_line_with_only_whitespace_is_a_no_op():
    fake = FakeExecutor()
    repl = Repl(executor=fake)
    run_line(repl, "   \n\t  ")
    assert fake.calls == [], \
        "blank input should not invoke the executor"


# ---------------------------------------------------------------------------
# Meta-commands
# ---------------------------------------------------------------------------

def test_meta_save_word_writes_file(tmp_path: Path):
    repl = Repl(executor=FakeExecutor())
    run_line(repl, ": foo 1 ;")
    target = tmp_path / "foo.fs"
    run_line(repl, f":save foo {target}")
    assert target.read_text() == ": foo 1 ;\n", \
        f":save NAME PATH should write the source text; got {target.read_text()!r}"


def test_meta_save_session_writes_file(tmp_path: Path):
    repl = Repl(executor=FakeExecutor())
    run_line(repl, ": foo 1 ;")
    run_line(repl, ": bar 2 ;")
    target = tmp_path / "session.fs"
    run_line(repl, f":save {target}")
    text = target.read_text()
    assert ": foo 1 ;" in text and ": bar 2 ;" in text, \
        f":save PATH should include both defs; got {text!r}"


def test_meta_save_with_unknown_word_reports_error_without_crashing(tmp_path: Path):
    repl = Repl(executor=FakeExecutor())
    out = run_line(repl, f":save not-a-word {tmp_path / 'x.fs'}")
    assert "not-a-word" in out and "no word" in out.lower(), \
        f":save unknown should report a friendly error; got {out!r}"


def test_meta_words_lists_session_words():
    repl = Repl(executor=FakeExecutor())
    run_line(repl, ": foo 1 ;")
    run_line(repl, "synonym d dup")
    out = run_line(repl, ":words")
    assert "foo" in out and "d" in out, \
        f":words should list defined words; got {out!r}"


def test_meta_quit_raises_repl_exit():
    repl = Repl(executor=FakeExecutor())
    with pytest.raises(ReplExit):
        run_line(repl, ":quit")


def test_meta_unknown_command_reports_error_not_crash():
    repl = Repl(executor=FakeExecutor())
    out = run_line(repl, ":nonsense")
    assert "nonsense" in out and "unknown" in out.lower(), \
        f"unknown meta-command should report a clear error; got {out!r}"


# ---------------------------------------------------------------------------
# Errors propagate as messages, not crashes
# ---------------------------------------------------------------------------

def test_compile_error_is_returned_as_message_not_raised():
    repl = Repl(executor=FakeExecutor())
    out = run_line(repl, ": foo dup")  # missing ;
    assert "foo" in out or "expected" in out.lower() or "unterminated" in out.lower(), \
        f"compile error should be returned as a message; got {out!r}"
    assert "foo" not in repl.session.state.dictionary, \
        "a definition that failed to compile must not be registered"


def test_redefinition_warning_is_visible_in_output():
    repl = Repl(executor=FakeExecutor())
    run_line(repl, ": foo 1 ;")
    out = run_line(repl, ": foo 2 ;")
    assert "foo" in out and "redefin" in out.lower(), \
        f"redefining a word should surface the warning; got {out!r}"


def test_executor_exception_is_returned_as_message_not_raised():
    class BoomExecutor:
        def __call__(self, session, expression: str) -> str:
            raise RuntimeError("simulated build failure")

    repl = Repl(executor=BoomExecutor())
    out = run_line(repl, "1 2 + .")
    assert "build failure" in out.lower() or "error" in out.lower(), \
        f"executor errors should surface as messages; got {out!r}"


# ---------------------------------------------------------------------------
# Includes work in the REPL too
# ---------------------------------------------------------------------------

def test_repl_include_brings_definitions_into_session(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 99 ;")
    repl = Repl(executor=FakeExecutor(), include_dirs=[tmp_path])
    run_line(repl, "include helper.fs")
    assert "helped" in repl.session.state.dictionary, \
        "include in REPL should make the included words callable"
    assert "include helper.fs" in repl.session.include_lines, \
        "include line should be logged for later :save"
