from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from mzt.compiler import ProgramState, compile_increment
from mzt.dictionary import WordInfo
from mzt.ir import ColonDef
from mzt.primitives import is_primitive
from mzt.tokenizer import TokenKind, tokenize


REPL_SOURCE_NAME = "<repl>"


@dataclass
class Session:
    include_dirs: list[Path] = field(default_factory=list)
    state: ProgramState = field(default_factory=lambda: ProgramState(allow_redefinition=True))
    include_lines: list[str] = field(default_factory=list)
    _interactive_order: list[str] = field(default_factory=list)
    _line_count: int = 0

    def feed(self, source: str) -> list[ColonDef]:
        self._record_includes(source)
        line_name = f"{REPL_SOURCE_NAME}:{self._line_count}"
        self._line_count += 1
        defs = compile_increment(
            source,
            state=self.state,
            source_name=line_name,
            include_dirs=self.include_dirs or None,
        )
        for d in defs:
            info = self.state.dictionary.get(d.name)
            if info is not None and info.source.startswith(REPL_SOURCE_NAME):
                self._touch_interactive(d.name)
        return defs

    def _record_includes(self, source: str) -> None:
        for line in _extract_include_lines(source):
            if line not in self.include_lines:
                self.include_lines.append(line)

    def _touch_interactive(self, name: str) -> None:
        if name in self._interactive_order:
            self._interactive_order.remove(name)
        self._interactive_order.append(name)

    def interactive_defs(self) -> Iterator[WordInfo]:
        for name in self._interactive_order:
            info = self.state.dictionary.get(name)
            if info is not None:
                yield info


def _extract_include_lines(source: str) -> list[str]:
    tokens = tokenize(source, source="<extract>")
    lines: list[str] = []
    i = 0
    while i < len(tokens) - 1:
        token = tokens[i]
        if token.kind == TokenKind.WORD and token.value == "include":
            target = tokens[i + 1]
            lines.append(f"include {target.raw}")
            i += 2
            continue
        i += 1
    return lines


def save_word(session: Session, name: str, out_path: Path) -> None:
    if is_primitive(name):
        raise ValueError(f"cannot save {name!r}: it is a built-in primitive")
    info = session.state.dictionary.get(name)
    if info is None:
        raise KeyError(f"no word named {name!r} is defined in this session")
    if info.source_text is None:
        raise ValueError(f"no source text recorded for {name!r}")
    Path(out_path).write_text(info.source_text + "\n")


def save_session(session: Session, out_path: Path) -> None:
    Path(out_path).write_text(_render_session(session))


def _render_session(session: Session) -> str:
    chunks: list[str] = []
    chunks.extend(session.include_lines)
    chunks.extend(
        info.source_text for info in session.interactive_defs()
        if info.source_text is not None
    )
    if not chunks:
        return ""
    return "\n\n".join(chunks) + "\n"
