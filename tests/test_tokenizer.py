import pytest

from mzt.tokenizer import Token, TokenKind, tokenize


def _kinds(source: str) -> list[TokenKind]:
    return [t.kind for t in tokenize(source)]


def _values(source: str) -> list[object]:
    return [t.value for t in tokenize(source)]


@pytest.mark.parametrize(
    "source,expected_kind",
    [
        (":", TokenKind.COLON),
        (";", TokenKind.SEMI),
        ("42", TokenKind.NUMBER),
        ("-7", TokenKind.NUMBER),
        ("0", TokenKind.NUMBER),
        ("+", TokenKind.WORD),
        (".", TokenKind.WORD),
        ("dup", TokenKind.WORD),
        ("MAIN", TokenKind.WORD),
    ],
)
def test_classifies_single_token(source, expected_kind):
    [tok] = tokenize(source)
    assert tok.kind == expected_kind, \
        f"tokenize({source!r}) should yield kind {expected_kind.name}"


@pytest.mark.parametrize("source", ["", "    ", "\t\n  \n"])
def test_whitespace_only_yields_no_tokens(source):
    assert tokenize(source) == [], \
        f"whitespace-only source {source!r} should produce zero tokens"


def test_full_program_kinds():
    assert _kinds(": main 2 3 + . ;") == [
        TokenKind.COLON,
        TokenKind.WORD,
        TokenKind.NUMBER,
        TokenKind.NUMBER,
        TokenKind.WORD,
        TokenKind.WORD,
        TokenKind.SEMI,
    ], "': main 2 3 + . ;' should tokenize into the canonical M1 token sequence"


@pytest.mark.parametrize(
    "source,expected_value",
    [
        ("0", 0),
        ("1", 1),
        ("42", 42),
        ("-7", -7),
        ("9999999999", 9999999999),
    ],
)
def test_number_value_is_int(source, expected_value):
    [tok] = tokenize(source)
    assert tok.value == expected_value, \
        f"number token from {source!r} should carry int {expected_value}"


def test_word_value_is_string():
    [tok] = tokenize("foo")
    assert tok.value == "foo", "word tokens should carry the original source string"


def test_line_numbers_track_source_lines():
    tokens = tokenize("1\n2\n3")
    assert [t.line for t in tokens] == [1, 2, 3], \
        "each token should know which 1-indexed source line it came from"


@pytest.mark.parametrize(
    "source",
    [
        "( comment ) 42",
        "42 ( trailing )",
        "( a ) 42 ( b )",
        "( multi word comment with symbols + - . ) 42",
    ],
)
def test_paren_comments_are_dropped(source):
    assert _values(source) == [42], \
        f"paren comments in {source!r} should leave only the 42 token"


def test_backslash_starts_line_comment():
    assert _values("42 \\ this is ignored\n7") == [42, 7], \
        "backslash should comment out the rest of its line and nothing more"


def test_dataclass_is_hashable():
    a = Token(TokenKind.NUMBER, 1, 1)
    b = Token(TokenKind.NUMBER, 1, 1)
    assert {a, b} == {a}, "Tokens with equal fields should compare and hash equal"
