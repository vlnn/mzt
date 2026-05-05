import pytest

from mzt.primitives import is_primitive, primitive


@pytest.mark.parametrize("name", ["+", "."])
def test_known_primitives(name):
    assert is_primitive(name), f"{name!r} should be recognised as a primitive in M1"


@pytest.mark.parametrize("name", ["dup", "drop", "swap", "*", "made-up-word", ""])
def test_unknown_primitives(name):
    assert not is_primitive(name), \
        f"{name!r} should not be a primitive yet (lands in later milestones)"


@pytest.mark.parametrize(
    "name,expected_label",
    [("+", "_plus"), (".", "_dot")],
)
def test_primitive_has_assembly_label(name, expected_label):
    assert primitive(name).label == expected_label, \
        f"{name!r} should compile to label {expected_label!r}"


@pytest.mark.parametrize("name", ["+", "."])
def test_primitive_body_is_nonempty(name):
    body = primitive(name).body
    assert body.strip(), \
        f"{name!r} primitive should have a non-empty assembly body"
