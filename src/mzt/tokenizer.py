import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    COLON = auto()
    SEMI = auto()
    NUMBER = auto()
    WORD = auto()
    STRING = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: object
    line: int


class TokenizerError(Exception):
    pass


_INT_RE = re.compile(r"^-?\d+$")
_DOT_QUOTE = '."'


def tokenize(source: str) -> list[Token]:
    cursor = _Cursor(source)
    tokens: list[Token] = []
    while not cursor.eof():
        cursor.skip_whitespace()
        if cursor.eof():
            break
        if cursor.match_word("\\"):
            cursor.skip_to_newline()
            continue
        if cursor.match_word("("):
            cursor.skip_paren_comment()
            continue
        if cursor.match_word(_DOT_QUOTE):
            tokens.append(cursor.read_string_token())
            continue
        tokens.append(cursor.read_word_token())
    return tokens


class _Cursor:
    __slots__ = ("source", "pos", "line")

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1

    def eof(self) -> bool:
        return self.pos >= len(self.source)

    def _advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.pos < len(self.source) and self.source[self.pos] == "\n":
                self.line += 1
            self.pos += 1

    def skip_whitespace(self) -> None:
        while not self.eof() and self.source[self.pos].isspace():
            self._advance()

    def skip_to_newline(self) -> None:
        while not self.eof() and self.source[self.pos] != "\n":
            self._advance()

    def skip_paren_comment(self) -> None:
        while not self.eof() and self.source[self.pos] != ")":
            self._advance()
        if not self.eof():
            self._advance()

    def match_word(self, word: str) -> bool:
        end = self.pos + len(word)
        if end > len(self.source):
            return False
        if self.source[self.pos:end] != word:
            return False
        if end < len(self.source) and not self.source[end].isspace():
            return False
        self._advance(len(word))
        return True

    def read_string_token(self) -> Token:
        opening_line = self.line
        if not self.eof() and self.source[self.pos] == " ":
            self._advance()
        start = self.pos
        while not self.eof() and self.source[self.pos] != '"':
            self._advance()
        if self.eof():
            raise TokenizerError(
                f"line {opening_line}: unterminated string literal"
            )
        content = self.source[start:self.pos]
        self._advance()
        return Token(TokenKind.STRING, content, opening_line)

    def read_word_token(self) -> Token:
        word_line = self.line
        start = self.pos
        while not self.eof() and not self.source[self.pos].isspace():
            self._advance()
        return _classify(self.source[start:self.pos], word_line)


def _classify(word: str, line: int) -> Token:
    if word == ":":
        return Token(TokenKind.COLON, ":", line)
    if word == ";":
        return Token(TokenKind.SEMI, ";", line)
    if _INT_RE.match(word):
        return Token(TokenKind.NUMBER, int(word), line)
    return Token(TokenKind.WORD, word, line)
