from pathlib import Path

import pytest

from mzt.repl_executor import (
    STATE_END_MARKER,
    STATE_START_MARKER,
    ClangExecutor,
    StackError,
    parse_state_dump,
    render_prelude,
    render_state_epilogue,
)
from mzt.session import Session


# ---------------------------------------------------------------------------
# State container & parsing — pure functions, no clang involved
# ---------------------------------------------------------------------------

def test_executor_starts_with_empty_state():
    e = ClangExecutor()
    assert e.data_stack == [], "fresh executor should have empty data stack"
    assert e.return_stack == [], "fresh executor should have empty return stack"
    assert e.variables == {}, "fresh executor should have no variable values"


def test_parse_state_dump_extracts_data_stack():
    raw = (
        "user output\n"
        f"{STATE_START_MARKER}\n"
        "DSTACK 3\n"
        "1\n2\n3\n"
        "RSTACK 0\n"
        "VARS 0\n"
        f"{STATE_END_MARKER}\n"
    )
    user_output, state = parse_state_dump(raw)
    assert user_output == "user output\n", \
        f"user output should be everything before the marker; got {user_output!r}"
    assert state.data_stack == [1, 2, 3], \
        f"data stack should be parsed bottom-to-top; got {state.data_stack!r}"


def test_parse_state_dump_extracts_return_stack():
    raw = (
        f"{STATE_START_MARKER}\n"
        "DSTACK 0\n"
        "RSTACK 2\n"
        "10\n20\n"
        "VARS 0\n"
        f"{STATE_END_MARKER}\n"
    )
    _, state = parse_state_dump(raw)
    assert state.return_stack == [10, 20], \
        f"return stack should round-trip; got {state.return_stack!r}"


def test_parse_state_dump_extracts_variables():
    raw = (
        f"{STATE_START_MARKER}\n"
        "DSTACK 0\n"
        "RSTACK 0\n"
        "VARS 2\n"
        "foo 42\n"
        "bar -7\n"
        f"{STATE_END_MARKER}\n"
    )
    _, state = parse_state_dump(raw)
    assert state.variables == {"foo": 42, "bar": -7}, \
        f"variables should round-trip; got {state.variables!r}"


def test_parse_state_dump_with_no_user_output_yields_empty_string():
    raw = (
        f"{STATE_START_MARKER}\n"
        "DSTACK 0\nRSTACK 0\nVARS 0\n"
        f"{STATE_END_MARKER}\n"
    )
    user_output, _ = parse_state_dump(raw)
    assert user_output == "", \
        f"no output before marker means empty string; got {user_output!r}"


def test_parse_state_dump_missing_markers_raises():
    with pytest.raises(StackError, match="state dump"):
        parse_state_dump("just user output, nothing else\n")


# ---------------------------------------------------------------------------
# Prelude / epilogue rendering
# ---------------------------------------------------------------------------

def test_render_prelude_with_empty_state_produces_empty_string():
    prelude = render_prelude(data_stack=[], return_stack=[], variables={})
    assert prelude == "", \
        f"nothing to restore should produce no prelude; got {prelude!r}"


def test_render_prelude_pushes_data_stack_in_bottom_to_top_order():
    prelude = render_prelude(data_stack=[1, 2, 3], return_stack=[], variables={})
    assert prelude == "1 2 3", \
        f"data stack values should appear bottom-to-top, space-separated; got {prelude!r}"


def test_render_prelude_pushes_return_stack_via_to_r():
    prelude = render_prelude(data_stack=[], return_stack=[10, 20], variables={})
    assert prelude == "10 >r 20 >r", \
        f"return stack values should each be pushed and moved to R; got {prelude!r}"


def test_render_prelude_writes_variable_values_via_store():
    prelude = render_prelude(data_stack=[], return_stack=[], variables={"foo": 42})
    assert prelude == "42 foo !", \
        f"variables should be restored via N name !; got {prelude!r}"


def test_render_prelude_combines_all_three_in_order():
    prelude = render_prelude(
        data_stack=[1, 2],
        return_stack=[99],
        variables={"x": 5},
    )
    assert prelude == "5 x ! 99 >r 1 2", \
        f"prelude should restore variables, then return stack, then data stack; got {prelude!r}"


def test_render_state_epilogue_contains_markers_and_dump_word():
    epilogue = render_state_epilogue(variable_names=["foo", "bar"])
    assert STATE_START_MARKER in epilogue, \
        "epilogue must emit the start marker"
    assert STATE_END_MARKER in epilogue, \
        "epilogue must emit the end marker"
    for name in ("foo", "bar"):
        assert name in epilogue, \
            f"epilogue should reference variable {name!r}"


# ---------------------------------------------------------------------------
# End-to-end with mocked clang — verify the full plumbing
# ---------------------------------------------------------------------------

def test_executor_pushes_results_onto_persistent_data_stack(mocker):
    _mock_build(mocker)
    _mock_run(mocker, dump_stdout(data_stack=[7]))
    e = ClangExecutor()
    e(Session(), "4 3 +")
    assert e.data_stack == [7], \
        f"after 4 3 + the executor's data stack should contain [7]; got {e.data_stack!r}"


def test_executor_data_stack_persists_across_two_lines(mocker):
    build = _mock_build(mocker)
    run = _mock_run_sequence(mocker, [
        dump_stdout(data_stack=[7]),
        dump_stdout(data_stack=[7, 1]),
    ])
    e = ClangExecutor()
    s = Session()
    e(s, "4 3 +")
    e(s, "2 1 -")
    second_program = build.call_args_list[1].args[0]
    assert "7" in second_program, \
        f"second build should re-push 7 from the saved stack; got program: {second_program!r}"


def test_executor_dot_pops_value_and_returns_user_output(mocker):
    build = _mock_build(mocker)
    _mock_run(mocker, "7\n" + dump_stdout(data_stack=[]))
    e = ClangExecutor()
    e.data_stack = [7]
    out = e(Session(), ".")
    assert out == "7\n", \
        f"executor should return only the user-visible part; got {out!r}"
    assert e.data_stack == [], \
        f"after . the data stack should be empty; got {e.data_stack!r}"


def test_executor_strips_state_dump_from_user_output(mocker):
    _mock_build(mocker)
    _mock_run(mocker, "hello\n" + dump_stdout(data_stack=[1, 2]))
    e = ClangExecutor()
    out = e(Session(), '." hello"')
    assert STATE_START_MARKER not in out, \
        "state markers must never leak into user-visible output"
    assert out == "hello\n", \
        f"only user-printed text should be returned; got {out!r}"


def test_executor_persists_variable_values_across_lines(mocker):
    build = _mock_build(mocker)
    _mock_run_sequence(mocker, [
        dump_stdout(variables={"foo": 0}),
        dump_stdout(variables={"foo": 42}),
        "42\n" + dump_stdout(variables={"foo": 42}),
    ])
    e = ClangExecutor()
    s = Session()
    s.feed("variable foo")
    e(s, "")
    e(s, "42 foo !")
    assert e.variables == {"foo": 42}, \
        f"after store, executor should remember foo=42; got {e.variables!r}"
    e(s, "foo @ .")
    second_to_last = build.call_args_list[-1].args[0]
    assert "42 foo !" in second_to_last, \
        "the program for the third line must restore foo's value before running"


def test_executor_clears_state_when_binary_crashes(mocker):
    _mock_build(mocker)
    run = mocker.patch("mzt.repl_executor.subprocess.run")
    run.return_value = mocker.Mock(stdout="oops\n", stderr="segfault\n", returncode=1)
    e = ClangExecutor()
    e.data_stack = [1, 2, 3]
    e.return_stack = [99]
    out = e(Session(), "broken")
    assert e.data_stack == [], \
        "after a crash the data stack must reset (state is undefined)"
    assert e.return_stack == [], \
        "after a crash the return stack must reset"
    assert "segfault" in out or "oops" in out, \
        f"crash output should still be surfaced; got {out!r}"


def test_executor_reset_clears_all_three_mirrors():
    e = ClangExecutor()
    e.data_stack = [1, 2]
    e.return_stack = [3]
    e.variables = {"x": 4}
    e.reset()
    assert e.data_stack == [] and e.return_stack == [] and e.variables == {}, \
        "reset() should clear all mirrors"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dump_stdout(*, data_stack=(), return_stack=(), variables=None) -> str:
    variables = variables or {}
    lines = [STATE_START_MARKER]
    lines.append(f"DSTACK {len(data_stack)}")
    lines.extend(str(v) for v in data_stack)
    lines.append(f"RSTACK {len(return_stack)}")
    lines.extend(str(v) for v in return_stack)
    lines.append(f"VARS {len(variables)}")
    lines.extend(f"{n} {v}" for n, v in variables.items())
    lines.append(STATE_END_MARKER)
    return "\n".join(lines) + "\n"


def _mock_build(mocker):
    return mocker.patch("mzt.repl_executor.build_source_text")


def _mock_run(mocker, stdout: str, *, returncode: int = 0):
    run = mocker.patch("mzt.repl_executor.subprocess.run")
    run.return_value = mocker.Mock(stdout=stdout, stderr="", returncode=returncode)
    return run


def _mock_run_sequence(mocker, stdouts: list[str]):
    run = mocker.patch("mzt.repl_executor.subprocess.run")
    run.side_effect = [
        mocker.Mock(stdout=s, stderr="", returncode=0) for s in stdouts
    ]
    return run
