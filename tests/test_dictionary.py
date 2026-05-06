import pytest

from mzt.dictionary import Dictionary, WordInfo


def test_new_dictionary_is_empty_and_falsy():
    d = Dictionary()
    assert len(d) == 0, "fresh dictionary should report length 0"
    assert "foo" not in d, "fresh dictionary should not contain anything"


def test_register_then_lookup():
    d = Dictionary()
    d.register("dup", kind="colon", source="hello.fs", line=3)
    assert "dup" in d, "after register, the name should be findable via 'in'"
    assert d.get("dup").kind == "colon", \
        "stored WordInfo should carry the kind passed at registration"
    assert d.get("dup").line == 3, \
        "stored WordInfo should carry the source line passed at registration"


def test_get_returns_none_when_absent():
    d = Dictionary()
    assert d.get("nope") is None, "get on missing name should return None, not raise"


def test_register_returns_the_word_info():
    d = Dictionary()
    info = d.register("dup", kind="colon", source="hello.fs", line=3)
    assert isinstance(info, WordInfo), \
        "register should return the WordInfo it stored"
    assert info.name == "dup", "returned WordInfo should carry the registered name"


def test_iteration_yields_names():
    d = Dictionary()
    d.register("a", kind="colon", source="x.fs", line=1)
    d.register("b", kind="variable", source="x.fs", line=2)
    assert list(d) == ["a", "b"], "iteration should yield names in insertion order"


def test_redefinition_warning_message_shape():
    d = Dictionary()
    d.register("foo", kind="colon", source="hello.fs", line=3)
    msg = d.redefinition_warning("foo", source="hello.fs", line=10)
    assert msg is not None, \
        "redefinition_warning should produce a message when name is already registered"
    assert "hello.fs:10" in msg, \
        "warning should locate the new definition (here:line)"
    assert "hello.fs:3" in msg, \
        "warning should reference where the previous definition lived (there:line)"
    assert "redefining" in msg and "foo" in msg, \
        "warning text should say what is being redefined"


def test_redefinition_warning_returns_none_for_new_name():
    d = Dictionary()
    msg = d.redefinition_warning("foo", source="hello.fs", line=1)
    assert msg is None, \
        "redefinition_warning on a name not yet registered should return None"


def test_register_overwrites_previous_entry():
    d = Dictionary()
    d.register("foo", kind="colon", source="a.fs", line=1)
    d.register("foo", kind="variable", source="b.fs", line=5)
    info = d.get("foo")
    assert (info.kind, info.source, info.line) == ("variable", "b.fs", 5), \
        "register should overwrite the entry — collision detection is the caller's job"


def test_word_info_is_frozen():
    info = WordInfo(name="foo", kind="colon", source="x.fs", line=1)
    with pytest.raises(Exception):
        info.line = 99  # type: ignore[misc]


def test_word_info_carries_all_four_fields():
    info = WordInfo(name="abs", kind="colon", source="math.fs", line=42)
    assert (info.name, info.kind, info.source, info.line) == \
        ("abs", "colon", "math.fs", 42), \
        "WordInfo should round-trip the four fields it accepts"
