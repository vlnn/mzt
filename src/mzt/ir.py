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


Cell = Literal | PrimRef | ColonRef | Label | Branch | StringLit


@dataclass(frozen=True)
class ColonDef:
    name: str
    body: tuple[Cell, ...]
