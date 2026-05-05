import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    COLON = auto()
    SEMI = auto()
    NUMBER = auto()
    WORD = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: object
    line: int


_INT_RE = re.compile(r"^-?\d+$")


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    for line_no, raw in enumerate(source.splitlines(), start=1):
        tokens.extend(_tokenize_line(raw, line_no))
    return tokens


def _tokenize_line(line: str, line_no: int) -> list[Token]:
    tokens: list[Token] = []
    words = iter(line.split())
    for word in words:
        if word == "\\":
            return tokens
        if word == "(":
            _consume_paren_comment(words)
            continue
        tokens.append(_classify(word, line_no))
    return tokens


def _consume_paren_comment(words) -> None:
    for word in words:
        if word == ")":
            return


def _classify(word: str, line_no: int) -> Token:
    if word == ":":
        return Token(TokenKind.COLON, ":", line_no)
    if word == ";":
        return Token(TokenKind.SEMI, ";", line_no)
    if _INT_RE.match(word):
        return Token(TokenKind.NUMBER, int(word), line_no)
    return Token(TokenKind.WORD, word, line_no)
