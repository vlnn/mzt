from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal


WordKind = Literal["colon", "variable", "create"]


@dataclass(frozen=True)
class WordInfo:
    name: str
    kind: WordKind
    source: str
    line: int


class Dictionary:

    def __init__(self) -> None:
        self._words: dict[str, WordInfo] = {}

    def __len__(self) -> int:
        return len(self._words)

    def __contains__(self, name: str) -> bool:
        return name in self._words

    def __iter__(self) -> Iterator[str]:
        return iter(self._words)

    def get(self, name: str) -> WordInfo | None:
        return self._words.get(name)

    def register(self, name: str, *, kind: WordKind, source: str, line: int) -> WordInfo:
        info = WordInfo(name=name, kind=kind, source=source, line=line)
        self._words[name] = info
        return info

    def redefinition_warning(self, name: str, *, source: str, line: int) -> str | None:
        previous = self._words.get(name)
        if previous is None:
            return None
        here = f"{source}:{line}"
        there = f"{previous.source}:{previous.line}"
        return f"{here}: warning: redefining {name!r} (first defined at {there})"
