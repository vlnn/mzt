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
        ("add.fs",        "5\n"),
        ("arith.fs",      "21\n"),
        ("square.fs",     "100\n"),
        ("abs.fs",        "7\n"),
        ("ifelse.fs",     "42\n"),
        ("countdown.fs",  "5\n4\n3\n2\n1\n"),
        ("fact.fs",       "120\n"),
        ("hello-text.fs", "Hello, world!\n"),
        ("letter.fs",     "A\n"),
        ("greet.fs",      "Hello, mzt!\n"),
        ("peephole.fs",   "7\n"),
        ("counter.fs",    "3\n"),
        ("buffer.fs",     "Hi!\n"),
        ("array-sum.fs",  "15\n"),
        ("rstack.fs",     "50\n"),
        ("rstack-stash.fs", "56\n"),
        ("regress-iter-countdown.fs", "5\n4\n3\n2\n1\n"),
        ("regress-iter-sum.fs",       "15\n"),
        ("regress-iter-search.fs",    "12\n"),
        ("do-count.fs",   "0\n1\n2\n3\n4\n"),
        ("do-sum.fs",     "15\n"),
        ("do-leave.fs",   "14\n"),
        ("do-nested.fs",  "1\n2\n2\n4\n3\n6\n"),
        ("recurse-fact.fs",  "120\n"),
        ("constant-area.fs", "27\n"),
        ("noname-execute.fs", "12\n"),
        ("noname-thunk.fs",   "ABC\n"),
        ("noname-runner.fs",  "12\n12\n"),
        ("include-helpers.fs", "10\n16\n"),
        ("include-and-thunks.fs", "14\n25\n"),
        ("include-stdlib.fs", "8\n3\n"),
    ],
)
def test_compiles_and_runs(tmp_build_dir, source_name, expected_stdout):
    binary = build_source(EXAMPLES / source_name, tmp_build_dir / "out")
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=True
    )
    assert result.stdout == expected_stdout, \
        f"{source_name} should print {expected_stdout!r}, got {result.stdout!r}"
