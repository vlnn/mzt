from io import StringIO

from mzt.repl import Repl, ReplExit
from mzt.repl_driver import run_interactive


class FakeExecutor:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.calls: list[str] = []

    def __call__(self, session, expression: str) -> str:
        self.calls.append(expression)
        return self.output


def test_run_interactive_processes_lines_until_eof():
    repl = Repl(executor=FakeExecutor(output="ok\n"))
    stdin = StringIO(": foo 1 ;\nfoo .\n")
    stdout = StringIO()
    run_interactive(repl, stdin=stdin, stdout=stdout)
    assert "foo" in repl.session.state.dictionary, \
        "first line should have been compiled"
    assert "ok" in stdout.getvalue(), \
        f"executor output should reach stdout; got {stdout.getvalue()!r}"


def test_run_interactive_writes_prompt_per_line():
    repl = Repl(executor=FakeExecutor())
    stdin = StringIO(": foo 1 ;\n")
    stdout = StringIO()
    run_interactive(repl, stdin=stdin, stdout=stdout, prompt="mzt> ")
    assert stdout.getvalue().count("mzt> ") >= 1, \
        f"prompt should appear at least once per input line; got {stdout.getvalue()!r}"


def test_run_interactive_stops_on_quit():
    repl = Repl(executor=FakeExecutor())
    stdin = StringIO(":quit\n: should-not-define 1 ;\n")
    stdout = StringIO()
    run_interactive(repl, stdin=stdin, stdout=stdout)
    assert "should-not-define" not in repl.session.state.dictionary, \
        "lines after :quit should not be processed"


def test_run_interactive_keeps_going_after_a_compile_error():
    repl = Repl(executor=FakeExecutor())
    stdin = StringIO(": broken dup\n: works 1 ;\n")
    stdout = StringIO()
    run_interactive(repl, stdin=stdin, stdout=stdout)
    assert "works" in repl.session.state.dictionary, \
        "after a compile error the loop should continue and accept further input"


def test_run_interactive_handles_empty_input_cleanly():
    repl = Repl(executor=FakeExecutor())
    run_interactive(repl, stdin=StringIO(""), stdout=StringIO())
