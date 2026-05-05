import subprocess
import sys
from pathlib import Path

import pytest

from mzt.builder import build

EXAMPLES = Path(__file__).parent.parent / "examples"

apple_silicon_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="M0 hello binary is Mach-O arm64; only runs on Apple Silicon",
)


def test_build_writes_assembly_alongside_output(mocker, tmp_build_dir):
    mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    build(".text\n_main: ret\n", out)

    assert out.with_suffix(".s").read_text() == ".text\n_main: ret\n", \
        "build should persist the assembly text next to the output binary"


def test_build_returns_output_path(mocker, tmp_build_dir):
    mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    result = build("ignored", out)

    assert result == out, \
        "build should return the output path so callers can chain off it"


@pytest.mark.parametrize(
    "expected_token",
    ["clang", "-arch", "arm64", "-o"],
)
def test_clang_invocation_includes(mocker, tmp_build_dir, expected_token):
    run = mocker.patch("mzt.builder.subprocess.run")

    build("ignored", tmp_build_dir / "hello")

    cmd = run.call_args.args[0]
    assert expected_token in cmd, \
        f"clang invocation should include {expected_token!r}, got {cmd!r}"


def test_clang_targets_arm64_explicitly(mocker, tmp_build_dir):
    run = mocker.patch("mzt.builder.subprocess.run")

    build("ignored", tmp_build_dir / "hello")

    cmd = run.call_args.args[0]
    arch_value = cmd[cmd.index("-arch") + 1]
    assert arch_value == "arm64", \
        f"-arch flag should be followed by 'arm64', got {arch_value!r}"


def test_clang_writes_to_requested_output_path(mocker, tmp_build_dir):
    run = mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    build("ignored", out)

    cmd = run.call_args.args[0]
    output_value = cmd[cmd.index("-o") + 1]
    assert output_value == str(out), \
        f"-o flag should be followed by the requested output path, got {output_value!r}"


def test_build_propagates_clang_failure(mocker, tmp_build_dir):
    mocker.patch(
        "mzt.builder.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, ["clang"]),
    )

    with pytest.raises(subprocess.CalledProcessError):
        build("ignored", tmp_build_dir / "hello")


@apple_silicon_only
def test_m0_hello_runs(tmp_build_dir):
    asm_text = (EXAMPLES / "hello.s").read_text()

    binary = build(asm_text, tmp_build_dir / "hello")
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=True
    )

    assert result.stdout == "hello\n", \
        "M0 hand-written hello.s should print 'hello' followed by a newline"
