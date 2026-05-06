import re
import sys
from pathlib import Path

import pytest

from mzt.jit.host_lib import (
    HostLibraryBuildError,
    build_host_library,
    default_host_library_path,
    emit_host_library_asm,
)
from mzt.primitives import all_primitives


@pytest.fixture(scope="module")
def asm() -> str:
    return emit_host_library_asm()


def test_asm_does_not_define_main(asm: str):
    assert "_main:" not in asm, \
        "host library is loaded by Python; defining _main would clash with the host process"


def test_asm_does_not_emit_main_globl(asm: str):
    assert ".globl  _main" not in asm and ".globl _main" not in asm, \
        "host library must not declare _main exported"


def test_asm_globalises_print_str(asm: str):
    assert ".globl _print_str" in asm, \
        "_print_str is called from JIT'd code via bl, so it must be a globally resolvable symbol"


@pytest.mark.parametrize(
    "primitive",
    [p for p in all_primitives() if not p.inline],
    ids=lambda p: p.name,
)
def test_asm_globalises_every_non_inline_primitive(asm: str, primitive):
    assert f".globl {primitive.label}" in asm, \
        f"primitive {primitive.name!r} (label {primitive.label}) must be exported for dlsym"


@pytest.mark.parametrize(
    "primitive",
    [p for p in all_primitives() if p.inline],
    ids=lambda p: p.name,
)
def test_asm_does_not_export_inline_primitives(asm: str, primitive):
    assert f".globl {primitive.label}" not in asm, \
        f"inline primitive {primitive.name!r} has no body of its own and must not be exported"


@pytest.mark.parametrize(
    "primitive",
    [p for p in all_primitives() if not p.inline],
    ids=lambda p: p.name,
)
def test_asm_defines_every_non_inline_primitive_label(asm: str, primitive):
    assert re.search(rf"^{re.escape(primitive.label)}:", asm, re.MULTILINE), \
        f"label {primitive.label}: must appear so the linker can place the body"


def test_asm_includes_data_stack_zerofill(asm: str):
    assert "Ldstack_base" in asm and ".zerofill __DATA,__bss,Ldstack_base" in asm, \
        "data stack bss is referenced from __dump-stacks; must be in the same image"


def test_asm_includes_return_stack_zerofill(asm: str):
    assert "Lrstack_base" in asm and ".zerofill __DATA,__bss,Lrstack_base" in asm, \
        "return stack bss is referenced from __dump-stacks; must be in the same image"


def test_asm_includes_user_memory_zerofill(asm: str):
    assert "Luser_mem" in asm and ".zerofill __DATA,__bss,Luser_mem" in asm, \
        "user memory area must be present so future variable-using JIT code can reference it"


def test_asm_includes_format_strings(asm: str):
    for fmt in ("Lfmt_dot", "Lfmt_dump_dstack", "Lfmt_dump_rstack", "Lfmt_dump_cell"):
        assert fmt in asm, \
            f"format string {fmt} is referenced from primitives; must be in the same image"


def test_asm_uses_correct_text_section(asm: str):
    assert ".section __TEXT,__text" in asm, \
        "primitive bodies must live in __TEXT,__text so they are page-aligned and executable"


def test_asm_globalises_trampoline(asm: str):
    assert ".globl _trampoline" in asm, \
        "the JIT trampoline must be globally resolvable so Python can dlsym and call it"


def test_asm_globalises_get_dstack_top(asm: str):
    assert ".globl _get_dstack_top" in asm, \
        "exposing the data-stack top lets the executor initialize x19 from Python"


def test_asm_globalises_get_rstack_top(asm: str):
    assert ".globl _get_rstack_top" in asm, \
        "exposing the return-stack top lets the executor initialize x20 from Python"


def test_asm_defines_trampoline_label(asm: str):
    import re
    assert re.search(r"^_trampoline:", asm, re.MULTILINE), \
        "the trampoline body must be emitted with its label"


def test_asm_trampoline_body_calls_blr_x2(asm: str):
    assert "blr     x2" in asm or "blr\tx2" in asm or "blr x2" in asm, \
        "trampoline must blr to the JIT body whose address arrived in x2"


def test_asm_trampoline_writes_back_x19_and_x20(asm: str):
    assert "str     x19, [x3]" in asm or "str\tx19, [x3]" in asm or "str x19, [x3]" in asm, \
        "trampoline must store the post-execution x19 to the out-pointer at x3"
    assert "str     x20, [x4]" in asm or "str\tx20, [x4]" in asm or "str x20, [x4]" in asm, \
        "trampoline must store the post-execution x20 to the out-pointer at x4"


def test_asm_get_dstack_top_returns_base_plus_size(asm: str):
    assert "Ldstack_base@PAGE" in asm and "#8192" in asm, \
        "_get_dstack_top should compute Ldstack_base + DSTACK_BYTES into x0"


def test_default_host_library_path_is_under_build_dir():
    path = default_host_library_path()
    assert path.suffix == ".dylib", "host library is a Mach-O dynamic library"
    assert "build" in path.parts, \
        "default location should be under build/ so it is gitignored"


def test_default_host_library_path_is_repo_relative():
    path = default_host_library_path()
    assert not path.is_absolute() or "build" in path.parts, \
        "default path must be reachable from the repo root"


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="dylib build needs clang and macOS"
)
def test_build_host_library_produces_a_mach_o_dylib(tmp_path: Path):
    out = tmp_path / "libmzt_host_test.dylib"
    result = build_host_library(out)
    assert result == out, "build returns the path it wrote"
    assert out.exists() and out.stat().st_size > 0, \
        "build must produce a non-empty file at the requested path"
    head = out.read_bytes()[:4]
    assert head == b"\xcf\xfa\xed\xfe", \
        f"output should be a 64-bit little-endian Mach-O; got bytes {head!r}"


def test_build_host_library_raises_when_clang_missing(tmp_path: Path, mocker):
    mocker.patch(
        "mzt.jit.host_lib._run_clang",
        side_effect=FileNotFoundError("clang"),
    )
    with pytest.raises(HostLibraryBuildError, match="clang"):
        build_host_library(tmp_path / "libmzt_host.dylib")


def test_build_host_library_surfaces_clang_stderr(tmp_path: Path, mocker):
    mocker.patch(
        "mzt.jit.host_lib._run_clang",
        return_value=(1, "ld: symbol not found _bogus"),
    )
    with pytest.raises(HostLibraryBuildError, match="symbol not found"):
        build_host_library(tmp_path / "libmzt_host.dylib")
