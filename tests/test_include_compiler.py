from pathlib import Path

import pytest

from mzt.compiler import CompileError, compile_source


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def test_include_brings_in_definitions_from_another_file(workspace):
    helper = workspace / "helper.fs"
    helper.write_text(": double 2 * ;")
    main_path = workspace / "main.fs"
    main_path.write_text("include helper.fs : main 5 double ;")
    defs = compile_source(main_path.read_text(), source_path=main_path)
    names = {d.name for d in defs}
    assert "double" in names and "main" in names, \
        f"include helper.fs should pull in 'double' alongside main; got {names}"


def test_include_resolves_via_include_dirs(workspace):
    lib_dir = workspace / "lib"
    src_dir = workspace / "src"
    lib_dir.mkdir(); src_dir.mkdir()
    (lib_dir / "shared.fs").write_text(": shared 99 ;")
    main_path = src_dir / "main.fs"
    main_path.write_text("include shared.fs : main shared ;")
    defs = compile_source(
        main_path.read_text(),
        source_path=main_path,
        include_dirs=[lib_dir],
    )
    names = {d.name for d in defs}
    assert "shared" in names and "main" in names, \
        "shared.fs from include_dirs should be picked up when missing from source dir"


def test_include_missing_file_raises_with_helpful_message(workspace):
    main_path = workspace / "main.fs"
    main_path.write_text("include nope.fs")
    with pytest.raises(CompileError, match="nope.fs"):
        compile_source(main_path.read_text(), source_path=main_path)


def test_include_at_top_level_with_no_filename_raises(workspace):
    main_path = workspace / "main.fs"
    main_path.write_text("include")
    with pytest.raises(CompileError, match="include"):
        compile_source(main_path.read_text(), source_path=main_path)


def test_include_inside_colon_body_raises(workspace):
    helper = workspace / "helper.fs"
    helper.write_text(": helper ;")
    main_path = workspace / "main.fs"
    main_path.write_text(": main include helper.fs ;")
    with pytest.raises(CompileError, match="include"):
        compile_source(main_path.read_text(), source_path=main_path)


def test_same_file_included_twice_processed_only_once(workspace):
    helper = workspace / "helper.fs"
    helper.write_text(": helper 1 ;")
    main_path = workspace / "main.fs"
    main_path.write_text(
        "include helper.fs include helper.fs : main helper ;"
    )
    # Without dedup, ': helper' would be defined twice → "already defined" error.
    # With dedup, second include is skipped.
    defs = compile_source(main_path.read_text(), source_path=main_path)
    helper_count = sum(1 for d in defs if d.name == "helper")
    assert helper_count == 1, \
        f"a file included twice should produce only one copy of its definitions; got {helper_count}"


def test_include_cycle_handled_via_dedup(workspace):
    a = workspace / "a.fs"
    b = workspace / "b.fs"
    a.write_text("include b.fs : in-a 1 ;")
    b.write_text("include a.fs : in-b 2 ;")
    defs = compile_source(a.read_text(), source_path=a)
    names = {d.name for d in defs}
    # Either order is fine; cycle must NOT cause infinite recursion or duplicate def errors.
    assert "in-a" in names and "in-b" in names, \
        f"a/b cyclic include should still produce both definitions exactly once; got {names}"


def test_transitive_include_works(workspace):
    a = workspace / "a.fs"
    b = workspace / "b.fs"
    c = workspace / "c.fs"
    a.write_text("include b.fs : main c-val ;")
    b.write_text("include c.fs")
    c.write_text("42 constant c-val")
    defs = compile_source(a.read_text(), source_path=a)
    names = {d.name for d in defs}
    assert "c-val" in names and "main" in names, \
        "include is transitive: a→b→c should make c-val visible to main in a"


def test_included_files_register_with_their_own_source_in_errors(workspace):
    helper = workspace / "helper.fs"
    helper.write_text(": dup 99 ;")  # tries to redefine a primitive
    main_path = workspace / "main.fs"
    main_path.write_text("include helper.fs")
    with pytest.raises(CompileError, match="primitive"):
        compile_source(main_path.read_text(), source_path=main_path)


def test_include_with_relative_path_subdirectory(workspace):
    sub = workspace / "sub"
    sub.mkdir()
    helper = sub / "helper.fs"
    helper.write_text(": from-sub 7 ;")
    main_path = workspace / "main.fs"
    main_path.write_text("include sub/helper.fs : main from-sub ;")
    defs = compile_source(main_path.read_text(), source_path=main_path)
    assert any(d.name == "from-sub" for d in defs), \
        "include should accept relative paths with subdirectory components"


def test_include_without_source_path_uses_only_include_dirs_and_stdlib(workspace):
    lib_dir = workspace / "lib"
    lib_dir.mkdir()
    (lib_dir / "thing.fs").write_text(": thing 1 ;")
    # No source_path supplied — must work via include_dirs alone.
    defs = compile_source(
        "include thing.fs : main thing ;",
        include_dirs=[lib_dir],
    )
    assert any(d.name == "thing" for d in defs), \
        "include should work without a source_path when include_dirs is sufficient"
