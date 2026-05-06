from dataclasses import dataclass


@dataclass(frozen=True)
class Literal:
    value: int


@dataclass(frozen=True)
class PrimRef:
    name: str


@dataclass(frozen=True)
class ColonRef:
    name: str


@dataclass(frozen=True)
class Label:
    id: int


@dataclass(frozen=True)
class Branch:
    target: int
    conditional: bool


@dataclass(frozen=True)
class StringLit:
    content: str


@dataclass(frozen=True)
class Addr:
    offset: int


@dataclass(frozen=True)
class WordAddr:
    name: str


Cell = Literal | PrimRef | ColonRef | Label | Branch | StringLit | Addr | WordAddr


@dataclass(frozen=True)
class ColonDef:
    name: str
    body: tuple[Cell, ...]
    source_text: str | None = None
