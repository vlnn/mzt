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
