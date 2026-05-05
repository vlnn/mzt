import subprocess
import sys
from pathlib import Path

import pytest

from mzt.builder import build_source

EXAMPLES = Path(__file__).parent.parent / "examples"

apple_silicon_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="end-to-end tests build Mach-O arm64 binaries; Apple Silicon only",
)


@apple_silicon_only
@pytest.mark.parametrize(
    "source_name,expected_stdout",
    [
        ("add.fs", "5\n"),
    ],
)
def test_compiles_and_runs(tmp_build_dir, source_name, expected_stdout):
    binary = build_source(EXAMPLES / source_name, tmp_build_dir / "out")
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=True
    )
    assert result.stdout == expected_stdout, \
        f"{source_name} should print {expected_stdout!r}, got {result.stdout!r}"
