from pathlib import Path

import pytest

from mzt.include_resolver import IncludeNotFound, IncludeResolver


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def test_resolves_relative_to_including_file_first(workspace):
    project_dir = workspace / "project"
    project_dir.mkdir()
    main = project_dir / "main.fs"
    helper = project_dir / "helper.fs"
    main.write_text(": main ;")
    helper.write_text(": helper ;")
    resolver = IncludeResolver(bundled_stdlib_dir=None)
    resolved = resolver.resolve("helper.fs", main)
    assert resolved == helper.resolve(), \
        f"helper.fs should resolve relative to main.fs's directory; got {resolved}"


def test_resolves_in_include_dirs_when_not_in_source_dir(workspace):
    project_dir = workspace / "project"
    lib_dir = workspace / "lib"
    project_dir.mkdir()
    lib_dir.mkdir()
    main = project_dir / "main.fs"
    main.write_text(": main ;")
    target = lib_dir / "shared.fs"
    target.write_text(": shared ;")
    resolver = IncludeResolver(include_dirs=[lib_dir], bundled_stdlib_dir=None)
    resolved = resolver.resolve("shared.fs", main)
    assert resolved == target.resolve(), \
        "shared.fs should be found via include_dirs when missing from source dir"


def test_resolves_in_bundled_stdlib_as_last_resort(workspace):
    project_dir = workspace / "project"
    stdlib_dir = workspace / "stdlib"
    project_dir.mkdir()
    stdlib_dir.mkdir()
    main = project_dir / "main.fs"
    main.write_text(": main ;")
    target = stdlib_dir / "core.fs"
    target.write_text(": dup ;")
    resolver = IncludeResolver(bundled_stdlib_dir=stdlib_dir)
    resolved = resolver.resolve("core.fs", main)
    assert resolved == target.resolve(), \
        "core.fs should fall through to the bundled stdlib dir"


def test_search_order_prefers_source_dir_over_include_dirs(workspace):
    src_dir = workspace / "src"
    lib_dir = workspace / "lib"
    src_dir.mkdir()
    lib_dir.mkdir()
    main = src_dir / "main.fs"
    main.write_text(": main ;")
    local = src_dir / "shadow.fs"
    far = lib_dir / "shadow.fs"
    local.write_text(": local ;")
    far.write_text(": far ;")
    resolver = IncludeResolver(include_dirs=[lib_dir], bundled_stdlib_dir=None)
    resolved = resolver.resolve("shadow.fs", main)
    assert resolved == local.resolve(), \
        "include must prefer files in the including-source's directory over include_dirs"


def test_absolute_path_resolved_directly(workspace):
    target = workspace / "data.fs"
    target.write_text(": data ;")
    resolver = IncludeResolver(bundled_stdlib_dir=None)
    resolved = resolver.resolve(str(target), None)
    assert resolved == target.resolve(), \
        "an absolute filename should resolve to itself when the file exists"


def test_not_found_raises_with_searched_paths_in_message(workspace):
    project_dir = workspace / "project"
    project_dir.mkdir()
    main = project_dir / "main.fs"
    main.write_text(": main ;")
    resolver = IncludeResolver(bundled_stdlib_dir=None)
    with pytest.raises(IncludeNotFound, match="missing.fs"):
        resolver.resolve("missing.fs", main)


def test_seen_tracking_starts_empty():
    resolver = IncludeResolver(bundled_stdlib_dir=None)
    assert resolver.seen_paths() == frozenset(), \
        "a fresh resolver should report no seen files"


def test_seen_tracking_records_marked_paths(workspace):
    target = workspace / "f.fs"
    target.write_text(": f ;")
    resolver = IncludeResolver(bundled_stdlib_dir=None)
    resolver.mark_seen(target.resolve())
    assert resolver.has_seen(target.resolve()), \
        "a path passed to mark_seen should be reported by has_seen"


def test_search_order_falls_through_to_stdlib_only_after_include_dirs(workspace):
    src_dir = workspace / "src"
    lib_dir = workspace / "lib"
    stdlib = workspace / "std"
    src_dir.mkdir(); lib_dir.mkdir(); stdlib.mkdir()
    main = src_dir / "main.fs"; main.write_text(": main ;")
    in_stdlib = stdlib / "x.fs"; in_stdlib.write_text(": x ;")
    in_libdir = lib_dir / "x.fs"; in_libdir.write_text(": y ;")
    resolver = IncludeResolver(include_dirs=[lib_dir], bundled_stdlib_dir=stdlib)
    resolved = resolver.resolve("x.fs", main)
    assert resolved == in_libdir.resolve(), \
        "include_dirs should take precedence over the bundled stdlib"
