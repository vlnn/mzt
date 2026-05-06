import subprocess
import tempfile
from pathlib import Path

from mzt.builder import build_source_text
from mzt.session import Session


class ClangExecutor:

    def __call__(self, session: Session, expression: str) -> str:
        program_text = _stitch_program(session, expression)
        with tempfile.TemporaryDirectory(prefix="mzt-repl-") as tmpdir:
            binary_path = Path(tmpdir) / "expr"
            build_source_text(
                program_text,
                binary_path,
                include_dirs=list(session.include_dirs) or None,
            )
            return _run_and_capture(binary_path)


def _stitch_program(session: Session, expression: str) -> str:
    parts: list[str] = []
    for info in session.interactive_defs():
        if info.source_text is not None:
            parts.append(info.source_text)
    parts.append(f": main {expression} ;")
    return "\n".join(session.include_lines + parts) + "\n"


def _run_and_capture(binary_path: Path) -> str:
    result = subprocess.run(
        [str(binary_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return result.stdout + result.stderr
    return result.stdout
