"""Sanity tests for the Forth-side test harness.

The actual per-word collection happens in `conftest.py` via
`pytest_collect_file` — every `tests/**/test_*.fs` file's `: test-*`
words become individual pytest items automatically.

This file only contains tests that don't fit the auto-discovery model:
the negative-case fixture (verifying halt-on-failure actually halts)
and a check that auto-discovery is wired up at all.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from mzt.builder import build_source
from mzt.forth_test_runner import discover_test_words


FORTH_TESTS_DIR = Path(__file__).parent / "forth"
FAILING_FIXTURE = FORTH_TESTS_DIR / "_failing_test_fixture.fs"


apple_silicon_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Forth-side tests build Mach-O arm64 binaries; Apple Silicon only",
)


@apple_silicon_only
def test_failing_fixture_actually_fails(tmp_build_dir):
    """Sanity check that halt + assert-eq genuinely produce a non-zero
    exit code when an assertion fails. Without this, a broken assert-eq
    would silently mark every test as passing."""
    binary = build_source(FAILING_FIXTURE, tmp_build_dir / "failing")
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=False
    )
    assert result.returncode != 0, (
        "the failing fixture should exit non-zero — if exit code is 0, "
        "the test library's halt-on-failure path is broken"
    )
    assert "FAIL" in result.stdout, (
        f"the failing fixture should print 'FAIL'; got stdout {result.stdout!r}"
    )


def test_failing_fixture_exists():
    assert FAILING_FIXTURE.is_file(), (
        f"the negative-case fixture should exist at {FAILING_FIXTURE}"
    )


def test_test_files_have_test_words():
    """Every test_*.fs file should declare at least one : test-* word.
    A file with zero test words contributes zero pytest items, which
    is almost certainly a bug — file got renamed without its words
    being updated."""
    for path in FORTH_TESTS_DIR.glob("test_*.fs"):
        words = discover_test_words(path.read_text())
        assert len(words) >= 1, (
            f"{path.name} should declare at least one ': test-*' word; "
            f"discover_test_words returned {words}"
        )
