import subprocess
from pathlib import Path

from mzt.compiler import CompileError, compile_source, program_user_memory_size
from mzt.emitter import emit_program
from mzt.ir import ColonDef
from mzt.peephole import optimize


ENTRY_WORD = "main"


def build(asm_text: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    asm_path = _persist_assembly(asm_text, out_path)
    _invoke_clang(asm_path, out_path)
    return out_path


def build_source(
    source_path: Path,
    out_path: Path,
    *,
    include_dirs: "list[Path] | None" = None,
) -> Path:
    src = Path(source_path)
    asm = compile_to_asm(
        src.read_text(),
        source_path=src,
        include_dirs=include_dirs,
    )
    return build(asm, out_path)


def compile_to_asm(
    source: str,
    *,
    source_path: "Path | None" = None,
    include_dirs: "list[Path] | None" = None,
) -> str:
    defs = compile_source(
        source, source_path=source_path, include_dirs=include_dirs,
    )
    _require_entry(defs)
    user_memory_bytes = program_user_memory_size(
        source, source_path=source_path, include_dirs=include_dirs,
    )
    return emit_program(optimize(defs), user_memory_bytes=user_memory_bytes)


def _require_entry(defs: list[ColonDef]) -> None:
    if not any(d.name == ENTRY_WORD for d in defs):
        raise CompileError(
            f"program must define ': {ENTRY_WORD} ... ;' as the entry point"
        )


def _persist_assembly(asm_text: str, out_path: Path) -> Path:
    asm_path = out_path.with_suffix(".s")
    asm_path.write_text(asm_text)
    return asm_path


def _invoke_clang(asm_path: Path, out_path: Path) -> None:
    subprocess.run(_clang_command(asm_path, out_path), check=True)


def _clang_command(asm_path: Path, out_path: Path) -> list[str]:
    return ["clang", "-arch", "arm64", str(asm_path), "-o", str(out_path)]
