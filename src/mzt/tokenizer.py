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
    col: int = 1
    source: str = "<input>"
    raw: str | None = None
    start_offset: int = 0
    end_offset: int = 0

    def __post_init__(self) -> None:
        if self.raw is None:
            object.__setattr__(self, "raw", str(self.value))


class TokenizerError(Exception):
    def __init__(self, message: str, line: int, col: int, source: str) -> None:
        self.message = message
        self.line = line
        self.col = col
        self.source = source
        super().__init__(f"{source}:{line}:{col}: {message}")


_NUMBER_RE = re.compile(r"^-?[0-9]+$|^\$[0-9a-fA-F]+$|^%[01]+$")
_DOT_QUOTE = '."'


def tokenize(text: str, source: str = "<input>") -> list[Token]:
    cursor = _Cursor(text, source)
    tokens: list[Token] = []
    while not cursor.eof():
        cursor.skip_whitespace()
        if cursor.eof():
            break
        token_start = cursor.pos
        if cursor.match_word("\\"):
            cursor.skip_to_newline()
            continue
        if cursor.match_word("("):
            cursor.skip_paren_comment()
            continue
        if cursor.match_word(_DOT_QUOTE):
            tokens.append(cursor.read_string_token(token_start))
            continue
        tokens.append(cursor.read_word_token())
    return tokens


class _Cursor:
    __slots__ = ("text", "source", "pos", "line", "col")

    def __init__(self, text: str, source: str):
        self.text = text
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def eof(self) -> bool:
        return self.pos >= len(self.text)

    def _advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.pos >= len(self.text):
                return
            if self.text[self.pos] == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def skip_whitespace(self) -> None:
        while not self.eof() and self.text[self.pos].isspace():
            self._advance()

    def skip_to_newline(self) -> None:
        while not self.eof() and self.text[self.pos] != "\n":
            self._advance()

    def skip_paren_comment(self) -> None:
        while not self.eof() and self.text[self.pos] != ")":
            self._advance()
        if not self.eof():
            self._advance()

    def match_word(self, word: str) -> bool:
        end = self.pos + len(word)
        if end > len(self.text):
            return False
        if self.text[self.pos:end] != word:
            return False
        if end < len(self.text) and not self.text[end].isspace():
            return False
        self._advance(len(word))
        return True

    def read_string_token(self, token_start: int) -> Token:
        opening_line, opening_col = self.line, self.col
        if not self.eof() and self.text[self.pos] == " ":
            self._advance()
        start = self.pos
        while not self.eof() and self.text[self.pos] != '"':
            self._advance()
        if self.eof():
            raise TokenizerError(
                "unterminated string literal", opening_line, opening_col, self.source
            )
        content = self.text[start:self.pos]
        self._advance()
        end = self.pos
        return Token(
            TokenKind.STRING, content, opening_line, opening_col, self.source,
            raw=self.text[token_start:end],
            start_offset=token_start, end_offset=end,
        )

    def read_word_token(self) -> Token:
        word_line, word_col = self.line, self.col
        start = self.pos
        while not self.eof() and not self.text[self.pos].isspace():
            self._advance()
        end = self.pos
        raw = self.text[start:end]
        return _classify(raw, word_line, word_col, self.source, start, end)


def _classify(word: str, line: int, col: int, source: str, start: int, end: int) -> Token:
    common = dict(line=line, col=col, source=source, raw=word, start_offset=start, end_offset=end)
    if word == ":":
        return Token(TokenKind.COLON, ":", **common)
    if word == ";":
        return Token(TokenKind.SEMI, ";", **common)
    if _NUMBER_RE.match(word):
        return Token(TokenKind.NUMBER, _parse_number(word), **common)
    return Token(TokenKind.WORD, word, **common)


def _parse_number(word: str) -> int:
    if word.startswith("$"):
        return int(word[1:], 16)
    if word.startswith("%"):
        return int(word[1:], 2)
    return int(word)
