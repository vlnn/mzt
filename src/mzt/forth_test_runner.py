"""Forth-side test runner — discovery, synthesis, execution.

A Forth test file contains zero or more `: test-foo …;` colon definitions.
Each becomes one independently-run pytest item. To run a single test
word, the runner synthesises a tiny main (`: main test-foo ;`), strips
any existing main definition, builds the resulting program, runs it,
and reads the exit code: 0 = pass, non-zero = fail.

The test library (`tests/forth/test-lib.fs`) provides `assert-eq`,
`assert-true`, `assert-false`, all of which call `halt 1` on failure
and print a brief diagnostic.
"""
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mzt.builder import build_source_text


TEST_WORD_RE = re.compile(r"^\s*:\s+(test-\S+)", re.MULTILINE)
_MAIN_RE = re.compile(r"^\s*:\s+main\b[^;]*;", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class ForthRunResult:
    failed: bool
    exit_code: int
    stdout: str
    stderr: str


def discover_test_words(source: str) -> list[str]:
    return [m.group(1) for m in TEST_WORD_RE.finditer(source)]


def synthesize_test_main(source: str, test_word: str) -> str:
    stripped = _MAIN_RE.sub("", source)
    return stripped + f"\n: main {test_word} ;\n"


def compile_and_run_word(
    source: str,
    source_path: Path,
    test_word: str,
    *,
    build_dir: Path | None = None,
) -> ForthRunResult:
    program = synthesize_test_main(source, test_word)
    if build_dir is None:
        with tempfile.TemporaryDirectory() as tmp:
            return _build_and_run(program, source_path, test_word, Path(tmp))
    return _build_and_run(program, source_path, test_word, build_dir)


def _build_and_run(
    program: str, source_path: Path, test_word: str, build_dir: Path,
) -> ForthRunResult:
    binary = build_source_text(
        program, build_dir / test_word, source_path=source_path,
    )
    completed = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=False,
    )
    return ForthRunResult(
        failed=completed.returncode != 0,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
