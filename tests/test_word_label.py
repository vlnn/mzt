import pytest

from mzt.emitter import _word_label


@pytest.mark.parametrize(
    "name,expected",
    [
        ("foo",      "_word_foo"),
        ("foo-bar",  "_word_foo_bar"),
        ("?dup",     "_word__q_dup"),
        ("/",        "_word__slash_"),
        ("mod",      "_word_mod"),
        ("/mod",     "_word__slash_mod"),
        ("foo+",     "_word_foo_plus_"),
        ("foo!",     "_word_foo_store_"),
        ("foo@",     "_word_foo_fetch_"),
        ("=",        "_word__eq_"),
        ("<>",       "_word__lt__gt_"),
        ("max-items", "_word_max_items"),
    ],
)
def test_word_label_sanitises_known_characters(name, expected):
    assert _word_label(name) == expected, \
        f"_word_label({name!r}) should produce {expected!r} for clang assembly compatibility"


def test_word_label_replaces_unknown_chars_with_underscore():
    # Any character not alphanumeric and not in the replacement table maps to _.
    # Forth names rarely use exotic characters, but this guards against
    # surprising characters slipping through.
    assert _word_label("foo\xa0bar") == "_word_foo_bar", \
        "non-ASCII whitespace should map to underscore"


def test_word_label_does_not_clobber_underscore():
    assert _word_label("__noname_0") == "_word___noname_0", \
        "synthetic noname names with underscores should pass through unmodified"


def test_word_label_alphanumeric_passes_through():
    assert _word_label("ANSWER42") == "_word_ANSWER42", \
        "alphanumeric characters should pass through to the asm label"
