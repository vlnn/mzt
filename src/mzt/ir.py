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


Cell = Literal | PrimRef | ColonRef


@dataclass(frozen=True)
class ColonDef:
    name: str
    body: tuple[Cell, ...]
