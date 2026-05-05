import subprocess
from pathlib import Path


def build(asm_text: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    asm_path = _persist_assembly(asm_text, out_path)
    _invoke_clang(asm_path, out_path)
    return out_path


def _persist_assembly(asm_text: str, out_path: Path) -> Path:
    asm_path = out_path.with_suffix(".s")
    asm_path.write_text(asm_text)
    return asm_path


def _invoke_clang(asm_path: Path, out_path: Path) -> None:
    subprocess.run(_clang_command(asm_path, out_path), check=True)


def _clang_command(asm_path: Path, out_path: Path) -> list[str]:
    return ["clang", "-arch", "arm64", str(asm_path), "-o", str(out_path)]
