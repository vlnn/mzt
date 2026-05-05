import subprocess
from pathlib import Path

from mzt.compiler import CompileError, compile_source
from mzt.emitter import emit_program
from mzt.ir import ColonDef


ENTRY_WORD = "main"


def build(asm_text: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    asm_path = _persist_assembly(asm_text, out_path)
    _invoke_clang(asm_path, out_path)
    return out_path


def build_source(source_path: Path, out_path: Path) -> Path:
    asm = compile_to_asm(Path(source_path).read_text())
    return build(asm, out_path)


def compile_to_asm(source: str) -> str:
    defs = compile_source(source)
    _require_entry(defs)
    return emit_program(defs)


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
