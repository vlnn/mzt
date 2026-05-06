from pathlib import Path

import pytest

from mzt.repl_executor import ClangExecutor
from mzt.session import Session


def test_clang_executor_builds_session_source_plus_main_expression(mocker):
    build_text = mocker.patch("mzt.repl_executor.build_source_text")
    run_proc = mocker.patch("mzt.repl_executor.subprocess.run")
    run_proc.return_value = mocker.Mock(stdout="6\n", stderr="", returncode=0)

    session = Session()
    session.feed(": dbl 2 * ;")
    executor = ClangExecutor()
    output = executor(session, "3 dbl .")

    assert output == "6\n", \
        f"executor should return whatever the built binary printed; got {output!r}"
    assert build_text.called, \
        "ClangExecutor should call build_source_text exactly once per evaluation"
    program_text = build_text.call_args.args[0]
    assert ": dbl 2 * ;" in program_text, \
        f"built program should include session source; got {program_text!r}"
    assert ": main 3 dbl . ;" in program_text, \
        f"built program should wrap the expression in a synthetic main; got {program_text!r}"


def test_clang_executor_passes_include_dirs_through_to_builder(mocker, tmp_path):
    mocker.patch("mzt.repl_executor.build_source_text")
    run_proc = mocker.patch("mzt.repl_executor.subprocess.run")
    run_proc.return_value = mocker.Mock(stdout="", stderr="", returncode=0)

    session = Session(include_dirs=[tmp_path])
    executor = ClangExecutor()
    executor(session, "1 .")

    from mzt import repl_executor
    kwargs = repl_executor.build_source_text.call_args.kwargs
    assert kwargs.get("include_dirs") == [tmp_path], \
        f"executor should forward session include_dirs to the builder; got {kwargs!r}"


def test_clang_executor_returns_stderr_when_binary_fails(mocker):
    mocker.patch("mzt.repl_executor.build_source_text")
    run_proc = mocker.patch("mzt.repl_executor.subprocess.run")
    run_proc.return_value = mocker.Mock(stdout="partial\n", stderr="boom\n", returncode=1)

    session = Session()
    executor = ClangExecutor()
    output = executor(session, "1 .")

    assert "partial" in output, \
        f"stdout should still surface even when binary returns non-zero; got {output!r}"
    assert "boom" in output, \
        f"stderr should be visible to the REPL user when the run fails; got {output!r}"


def test_clang_executor_caches_session_dictionary_size_for_main_omission(mocker):
    """If the user types only definitions on a line, _split_defs_and_expression
    in the REPL keeps the expression empty. The executor must never be called
    in that case — it should not see a synthetic ': main ;' that prints
    nothing. This is a regression guard, not a feature: the REPL handles
    the no-expression case before reaching the executor."""
    build_text = mocker.patch("mzt.repl_executor.build_source_text")
    mocker.patch("mzt.repl_executor.subprocess.run")
    session = Session()
    executor = ClangExecutor()
    executor(session, "1 .")
    assert build_text.called, \
        "the executor must run when there's an expression"
