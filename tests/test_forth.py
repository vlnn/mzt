"""Forth-side test discovery: walks tests/forth/test-*.fs and runs each.

Each .fs file builds to a Mach-O executable; running the binary should
exit 0 if all in-program assertions pass. The Forth-side test library
calls `halt` with a non-zero code on first assertion failure.

This file is the bridge between mzt's existing pytest infrastructure
and the Forth-source test suite that grows with the language. After
this lands, *adding a new test is writing one .fs file* — no Python
boilerplate.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from mzt.builder import build_source


FORTH_TESTS_DIR = Path(__file__).parent / "forth"
FAILING_FIXTURE = FORTH_TESTS_DIR / "_failing-test-fixture.fs"


apple_silicon_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Forth-side tests build Mach-O arm64 binaries; Apple Silicon only",
)


def _discover_forth_tests() -> list[Path]:
    return sorted(
        p for p in FORTH_TESTS_DIR.glob("test-*.fs")
        if p.name != "test-lib.fs"
    )


@apple_silicon_only
@pytest.mark.parametrize(
    "source_path",
    _discover_forth_tests(),
    ids=lambda p: p.name,
)
def test_forth_test_passes(source_path, tmp_build_dir):
    binary = build_source(source_path, tmp_build_dir / source_path.stem)
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"Forth-side test {source_path.name} failed with exit code "
        f"{result.returncode}; stdout was: {result.stdout!r}"
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


def test_at_least_one_forth_test_exists():
    """Catches the regression where someone restructures the test directory
    and accidentally orphans the discovery."""
    discovered = _discover_forth_tests()
    assert len(discovered) >= 1, (
        f"expected at least one tests/forth/test-*.fs to be discovered; "
        f"got {discovered}"
    )


def test_failing_fixture_exists():
    assert FAILING_FIXTURE.is_file(), (
        f"the negative-case fixture should exist at {FAILING_FIXTURE}"
    )
