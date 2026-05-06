import subprocess
import sys
from pathlib import Path

from mzt.primitives import Primitive, all_primitives


_DSTACK_BYTES = 8192
_RSTACK_BYTES = 4096
_USER_MEMORY_BYTES = 16


class HostLibraryBuildError(RuntimeError):
    pass


def emit_host_library_asm() -> str:
    return (
        _exports()
        + _text_section_header()
        + _trampoline()
        + _stack_top_getters()
        + _print_str_helper()
        + "".join(_emit_primitive(p) for p in all_primitives() if not p.inline)
        + _rodata()
        + _bss()
    )


def default_host_library_path() -> Path:
    return Path("build") / "jit" / "libmzt_host.dylib"


def build_host_library(out_path: Path, *, asm: str | None = None) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    asm_text = asm if asm is not None else emit_host_library_asm()
    asm_path = out_path.with_suffix(".s")
    asm_path.write_text(asm_text)
    try:
        returncode, stderr = _run_clang(asm_path, out_path)
    except FileNotFoundError as exc:
        raise HostLibraryBuildError(f"clang not found on PATH: {exc}") from exc
    if returncode != 0:
        raise HostLibraryBuildError(
            f"clang failed with exit {returncode}:\n{stderr}"
        )
    return out_path


def _run_clang(asm_path: Path, out_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [
            "clang",
            *_clang_arch_flags(),
            "-dynamiclib",
            "-Wl,-undefined,dynamic_lookup",
            str(asm_path),
            "-o",
            str(out_path),
        ],
        capture_output=True,
    )
    return proc.returncode, proc.stderr.decode(errors="replace")


def _clang_arch_flags() -> list[str]:
    if sys.platform == "darwin":
        return ["-arch", "arm64"]
    return ["--target=arm64-apple-darwin"]


def _exports() -> str:
    lines = [
        ".globl _print_str",
        ".globl _trampoline",
        ".globl _get_dstack_top",
        ".globl _get_rstack_top",
    ]
    for primitive in all_primitives():
        if primitive.inline:
            continue
        lines.append(f".globl {primitive.label}")
    return "\n".join(lines) + "\n"


def _trampoline() -> str:
    return (
        "_trampoline:\n"
        "    stp     x29, x30, [sp, #-16]!\n"
        "    mov     x29, sp\n"
        "    stp     x19, x20, [sp, #-16]!\n"
        "    stp     x3, x4, [sp, #-16]!\n"
        "    mov     x19, x0\n"
        "    mov     x20, x1\n"
        "    blr     x2\n"
        "    ldp     x3, x4, [sp], #16\n"
        "    str     x19, [x3]\n"
        "    str     x20, [x4]\n"
        "    ldp     x19, x20, [sp], #16\n"
        "    ldp     x29, x30, [sp], #16\n"
        "    ret\n\n"
    )


def _stack_top_getters() -> str:
    return (
        "_get_dstack_top:\n"
        "    adrp    x0, Ldstack_base@PAGE\n"
        "    add     x0, x0, Ldstack_base@PAGEOFF\n"
        f"    add     x0, x0, #{_DSTACK_BYTES}\n"
        "    ret\n\n"
        "_get_rstack_top:\n"
        "    adrp    x0, Lrstack_base@PAGE\n"
        "    add     x0, x0, Lrstack_base@PAGEOFF\n"
        f"    add     x0, x0, #{_RSTACK_BYTES}\n"
        "    ret\n\n"
    )


def _text_section_header() -> str:
    return ".section __TEXT,__text,regular,pure_instructions\n.p2align 2\n\n"


def _print_str_helper() -> str:
    return (
        "_print_str:\n"
        "    stp     x29, x30, [sp, #-16]!\n"
        "    mov     x29, sp\n"
        "    mov     x2, x1\n"
        "    mov     x1, x0\n"
        "    mov     x0, #1\n"
        "    bl      _write\n"
        "    ldp     x29, x30, [sp], #16\n"
        "    ret\n\n"
    )


def _emit_primitive(p: Primitive) -> str:
    return f"{p.label}:\n{p.body}    ret\n\n"


def _rodata() -> str:
    return (
        "\n.section __TEXT,__cstring,cstring_literals\n"
        "Lfmt_dot:\n"
        '    .asciz  "%lld\\n"\n'
        "Lfmt_dump_dstack:\n"
        '    .asciz  "DSTACK %lld\\n"\n'
        "Lfmt_dump_rstack:\n"
        '    .asciz  "RSTACK %lld\\n"\n'
        "Lfmt_dump_cell:\n"
        '    .asciz  "%lld\\n"\n'
    )


def _bss() -> str:
    return (
        f"\n.zerofill __DATA,__bss,Ldstack_base,{_DSTACK_BYTES},3\n"
        f".zerofill __DATA,__bss,Lrstack_base,{_RSTACK_BYTES},3\n"
        f".zerofill __DATA,__bss,Luser_mem,{_USER_MEMORY_BYTES},3\n"
    )
