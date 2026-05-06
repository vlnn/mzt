from collections.abc import Iterator
from typing import Any


ControlFrame = tuple[str, Any]


class ControlStackError(Exception):
    pass


class ControlStack:

    def __init__(self) -> None:
        self._frames: list[ControlFrame] = []

    def __len__(self) -> int:
        return len(self._frames)

    def __bool__(self) -> bool:
        return bool(self._frames)

    def __iter__(self) -> Iterator[ControlFrame]:
        return iter(self._frames)

    def push(self, tag: str, value: Any) -> None:
        self._frames.append((tag, value))

    def pop(self, expected_tag: str) -> Any:
        tag, value = self._pop_or_underflow(expected_tag)
        if tag != expected_tag:
            raise ControlStackError(
                f"control flow mismatch: expected {expected_tag}, got {tag}"
            )
        return value

    def pop_any(self, expected_tags: list[str]) -> ControlFrame:
        context = "/".join(expected_tags)
        tag, value = self._pop_or_underflow(context)
        if tag not in expected_tags:
            raise ControlStackError(
                f"control flow mismatch: expected {context}, got {tag}"
            )
        return tag, value

    def peek(self) -> ControlFrame:
        if not self._frames:
            raise ControlStackError("control stack underflow")
        return self._frames[-1]

    def find_innermost(self, tag: str) -> ControlFrame | None:
        for frame in reversed(self._frames):
            if frame[0] == tag:
                return frame
        return None

    def clear(self) -> None:
        self._frames.clear()

    def _pop_or_underflow(self, context: str) -> ControlFrame:
        if not self._frames:
            raise ControlStackError(f"control stack underflow ({context})")
        return self._frames.pop()
