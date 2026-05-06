"""Pytest collection plugin: every `tests/**/test_*.fs` file is treated
like a Python test module. Each `: test-foo ;` colon definition becomes
one pytest item (e.g. ``tests/forth/test_arithmetic.fs::test-add``).

Run all of them:

    pytest tests/forth/

Filter by name:

    pytest -k arithmetic
    pytest tests/forth/test_arithmetic.fs::test-add

Forth tests skip on non-Apple-Silicon machines (clang produces Mach-O
arm64 binaries that only run there).
"""
import sys
from pathlib import Path

import pytest

from mzt.forth_test_runner import (
    ForthRunResult,
    compile_and_run_word,
    discover_test_words,
)


@pytest.fixture
def tmp_build_dir(tmp_path: Path) -> Path:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    return build_dir


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".fs" and file_path.name.startswith("test_"):
        return ForthFile.from_parent(parent, path=file_path)


class ForthFile(pytest.File):
    def collect(self):
        source = self.path.read_text()
        for word in discover_test_words(source):
            yield ForthItem.from_parent(self, name=word, source=source)


class ForthItem(pytest.Item):
    def __init__(self, *, name, parent, source):
        super().__init__(name, parent)
        self._source = source

    def runtest(self):
        if sys.platform != "darwin":
            pytest.skip(
                "Forth tests build Mach-O arm64 binaries; Apple Silicon only"
            )
        result = compile_and_run_word(self._source, self.path, self.name)
        if result.failed:
            raise ForthAssertionError(self.name, result)

    def repr_failure(self, excinfo, style=None):
        err = excinfo.value
        if not isinstance(err, ForthAssertionError):
            return super().repr_failure(excinfo, style)
        return _format_failure(err)

    def reportinfo(self):
        return self.path, None, f"forth: {self.name}"


class ForthAssertionError(Exception):
    def __init__(self, test_word: str, result: ForthRunResult):
        self.test_word = test_word
        self.result = result
        super().__init__(f"forth assertion failed in {test_word!r}")


def _format_failure(err: ForthAssertionError) -> str:
    lines = [
        f"Forth assertion failed in `{err.test_word}`",
        f"  exit code: {err.result.exit_code}",
    ]
    if err.result.stdout:
        lines.append("  stdout:")
        for line in err.result.stdout.splitlines():
            lines.append(f"    {line}")
    if err.result.stderr:
        lines.append("  stderr:")
        for line in err.result.stderr.splitlines():
            lines.append(f"    {line}")
    return "\n".join(lines)
