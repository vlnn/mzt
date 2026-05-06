import sys
from pathlib import Path

import pytest

from mzt.cli import main


def test_build_command_invokes_build_source(mocker, tmp_path):
    fake_build = mocker.patch("mzt.cli.build_source")
    src = tmp_path / "x.fs"
    src.write_text(": main 1 . ;\n")
    out = tmp_path / "x"

    rc = main(["build", str(src), "-o", str(out)])

    assert rc == 0, "successful build should return exit code 0"
    fake_build.assert_called_once_with(src, out), \
        "cli should pass the source and output paths through to build_source"


def test_build_command_reports_compile_error(mocker, tmp_path, capsys):
    from mzt.compiler import CompileError
    mocker.patch("mzt.cli.build_source", side_effect=CompileError("missing main"))

    rc = main(["build", str(tmp_path / "x.fs"), "-o", str(tmp_path / "x")])

    captured = capsys.readouterr()
    assert rc == 1, "compile errors should exit with code 1"
    assert "missing main" in captured.err, \
        "the compile error message should be written to stderr"


@pytest.mark.parametrize("argv", [[], ["build"], ["build", "x.fs"]])
def test_missing_arguments_exit_with_argparse_error(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code != 0, \
        f"argparse should reject incomplete invocation {argv!r} with non-zero exit"


def test_repl_without_jit_flag_uses_clang_executor(mocker):
    fake_run = mocker.patch("mzt.cli.run_interactive")
    fake_clang_executor = mocker.Mock()
    mocker.patch("mzt.cli.ClangExecutor", return_value=fake_clang_executor)
    fake_jit_factory = mocker.patch("mzt.cli._make_jit_executor")

    rc = main(["repl"])

    assert rc == 0, "repl with default executor should exit cleanly"
    fake_jit_factory.assert_not_called(), \
        "without --jit, the JIT executor must not be instantiated"
    assert fake_run.called, "run_interactive should have been invoked"


def test_repl_with_jit_flag_uses_jit_executor(mocker):
    mocker.patch("mzt.cli.run_interactive")
    fake_jit_executor = mocker.Mock()
    fake_factory = mocker.patch(
        "mzt.cli._make_jit_executor",
        return_value=fake_jit_executor,
    )

    rc = main(["repl", "--jit"])

    assert rc == 0, "repl --jit should exit cleanly when run_interactive returns"
    fake_factory.assert_called_once(), \
        "the --jit flag must trigger JIT executor creation exactly once"


def test_repl_with_jit_flag_closes_executor_on_exit(mocker):
    mocker.patch("mzt.cli.run_interactive")
    fake_executor = mocker.Mock()
    mocker.patch("mzt.cli._make_jit_executor", return_value=fake_executor)

    main(["repl", "--jit"])

    fake_executor.close.assert_called_once(), \
        "the JIT executor's close() must be called even on normal exit (releases JIT region)"


def test_repl_with_jit_flag_closes_executor_even_on_exception(mocker):
    mocker.patch("mzt.cli.run_interactive", side_effect=KeyboardInterrupt)
    fake_executor = mocker.Mock()
    mocker.patch("mzt.cli._make_jit_executor", return_value=fake_executor)

    with pytest.raises(KeyboardInterrupt):
        main(["repl", "--jit"])

    fake_executor.close.assert_called_once(), \
        "close() must run on exceptional exit too — JIT region must always be released"
