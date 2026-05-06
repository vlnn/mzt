from io import StringIO
from pathlib import Path

import pytest

from mzt.cli import main


def test_cli_repl_subcommand_exists(mocker):
    enter = mocker.patch("mzt.cli.run_interactive")
    main(["repl"])
    assert enter.called, \
        "the 'repl' subcommand should hand control to run_interactive"


def test_cli_repl_uses_clang_executor_by_default(mocker):
    captured = {}

    def fake_run(repl, **kwargs):
        captured["repl"] = repl

    mocker.patch("mzt.cli.run_interactive", side_effect=fake_run)
    main(["repl"])
    from mzt.repl_executor import ClangExecutor
    assert isinstance(captured["repl"].executor, ClangExecutor), \
        f"default executor should be ClangExecutor; got {type(captured['repl'].executor)}"


def test_cli_repl_accepts_include_dir(mocker, tmp_path: Path):
    captured = {}

    def fake_run(repl, **kwargs):
        captured["repl"] = repl

    mocker.patch("mzt.cli.run_interactive", side_effect=fake_run)
    main(["repl", "-I", str(tmp_path)])
    assert tmp_path in captured["repl"].include_dirs, \
        f"--include-dir should reach the Repl; got {captured['repl'].include_dirs!r}"


def test_cli_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as exc:
        main(["nonsense"])
    assert exc.value.code != 0, \
        "unknown subcommand should exit with non-zero status"
