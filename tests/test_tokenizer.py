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


def test_dot_quote_emits_string_token():
    [tok] = tokenize(': main ." Hello, world!" ;')[2:3]
    assert tok.kind == TokenKind.STRING, "'.\"' should produce a STRING token"
    assert tok.value == "Hello, world!", \
        "STRING token should carry the literal content between '.\"' and the closing quote"


@pytest.mark.parametrize(
    "source,expected_content",
    [
        ('." hi"',                 "hi"),
        ('." Hello, world!"',      "Hello, world!"),
        ('."  two leading spaces"', " two leading spaces"),
        ('." with ( fake comment )"', "with ( fake comment )"),
        ('." escaped \\ backslash"', "escaped \\ backslash"),
        ('." "',                   ""),
    ],
)
def test_string_content_preserved(source, expected_content):
    [tok] = [t for t in tokenize(source) if t.kind == TokenKind.STRING]
    assert tok.value == expected_content, \
        f"tokenize({source!r}) STRING content should be {expected_content!r}"


def test_string_can_span_multiple_lines():
    tokens = tokenize('." line one\nline two"')
    [s] = [t for t in tokens if t.kind == TokenKind.STRING]
    assert s.value == "line one\nline two", \
        "string content should preserve embedded newlines verbatim"


def test_unterminated_string_raises():
    from mzt.tokenizer import TokenizerError
    with pytest.raises(TokenizerError, match="unterminated"):
        tokenize(': main ." no closing quote ;')


def test_dot_quote_without_following_whitespace_is_a_word():
    tokens = tokenize(': main ."hi" ;')
    kinds = [t.kind for t in tokens]
    assert TokenKind.STRING not in kinds, \
        '\'.\"\' followed immediately by content (no space) is not a string opener'


def test_full_program_with_string():
    tokens = tokenize(': main ." hi" cr ;')
    kinds = [t.kind for t in tokens]
    assert kinds == [
        TokenKind.COLON, TokenKind.WORD, TokenKind.STRING, TokenKind.WORD, TokenKind.SEMI,
    ], "': main .\" hi\" cr ;' should tokenize as colon/word/string/word/semi"


def test_column_starts_at_one():
    [tok] = tokenize("dup")
    assert tok.col == 1, "first column on a line should be 1, not 0"


def test_column_tracks_position_within_line():
    a, b, c = tokenize("dup  drop swap")
    assert (a.col, b.col, c.col) == (1, 6, 11), \
        "columns should point to the first character of each token"


def test_column_resets_after_newline():
    tokens = tokenize("dup\n  drop")
    assert [(t.line, t.col) for t in tokens] == [(1, 1), (2, 3)], \
        "after a newline col should reset to 1 and advance from there"


def test_source_defaults_to_angled_input():
    [tok] = tokenize("dup")
    assert tok.source == "<input>", \
        "tokenize() with no source argument should label tokens as '<input>'"


def test_source_argument_is_threaded_into_tokens():
    [tok] = tokenize("dup", source="hello.fs")
    assert tok.source == "hello.fs", \
        "tokenize(source='hello.fs') should put 'hello.fs' on every token"


def test_raw_preserves_original_source_for_numbers():
    a, b, c = tokenize("$1a %1010 -7")
    assert (a.raw, b.raw, c.raw) == ("$1a", "%1010", "-7"), \
        "raw should preserve the original source spelling regardless of how value was parsed"


def test_raw_equals_value_for_words():
    [tok] = tokenize("dup")
    assert tok.raw == "dup", "for word tokens raw and value should agree"


@pytest.mark.parametrize(
    "source,expected_value",
    [
        ("$0",        0),
        ("$1",        1),
        ("$ff",       255),
        ("$1a",       26),
        ("$deadbeef", 0xDEADBEEF),
        ("$4000",     16384),
    ],
)
def test_hex_literals(source, expected_value):
    [tok] = tokenize(source)
    assert tok.kind == TokenKind.NUMBER, \
        f"{source!r} should classify as NUMBER, not WORD"
    assert tok.value == expected_value, \
        f"hex literal {source!r} should parse to {expected_value}"


@pytest.mark.parametrize(
    "source,expected_value",
    [
        ("%0",         0),
        ("%1",         1),
        ("%10",        2),
        ("%1010",      10),
        ("%11111111",  255),
        ("%10110010",  178),
    ],
)
def test_binary_literals(source, expected_value):
    [tok] = tokenize(source)
    assert tok.kind == TokenKind.NUMBER, \
        f"{source!r} should classify as NUMBER, not WORD"
    assert tok.value == expected_value, \
        f"binary literal {source!r} should parse to {expected_value}"


@pytest.mark.parametrize(
    "source",
    [
        "$",
        "%",
        "$xyz",
        "%012",
        "$-1",
        "%-1",
    ],
)
def test_invalid_radix_literals_classify_as_word(source):
    [tok] = tokenize(source)
    assert tok.kind == TokenKind.WORD, \
        f"{source!r} is not a well-formed number and should fall through to WORD"


def test_tokenizer_error_message_includes_source_filename():
    from mzt.tokenizer import TokenizerError
    with pytest.raises(TokenizerError, match="hello.fs"):
        tokenize(': main ." no closing quote ;', source="hello.fs")


def test_backslash_without_trailing_whitespace_is_a_word():
    [tok] = tokenize(r"\foo")
    assert tok.kind == TokenKind.WORD and tok.value == r"\foo", \
        r"'\foo' (no space after the backslash) must be a word, not a comment marker"


def test_paren_without_trailing_whitespace_is_a_word():
    [tok] = tokenize("(noop)")
    assert tok.kind == TokenKind.WORD and tok.value == "(noop)", \
        "'(noop)' is a single word — paren only opens a comment when whitespace-bounded"


def test_paren_comment_still_works_when_whitespace_bounded():
    assert _values("42 ( ignored ) 7") == [42, 7], \
        "'( ... )' with whitespace around the paren should still drop content"
