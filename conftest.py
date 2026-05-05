from pathlib import Path

import pytest


@pytest.fixture
def tmp_build_dir(tmp_path: Path) -> Path:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    return build_dir
