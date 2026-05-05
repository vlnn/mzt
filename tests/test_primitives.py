import pytest

from mzt.primitives import all_primitives, is_primitive, primitive


M2_NAMES = [
    "dup", "drop", "swap", "over", "nip", "rot",
    "+", "-", "*", "/mod",
    "=", "<", ">", "0=",
    "and", "or", "xor", "invert",
    "negate", "abs",
    ".",
]


@pytest.mark.parametrize("name", M2_NAMES)
def test_known_primitives(name):
    assert is_primitive(name), \
        f"{name!r} should be registered as a primitive at M2"


@pytest.mark.parametrize(
    "name",
    ["if", "then", "else", "begin", "until", "do", "loop",
     "@", "!", "variable", "made-up-word", ""],
)
def test_unknown_primitives(name):
    assert not is_primitive(name), \
        f"{name!r} should NOT be a primitive yet (lands in later milestones)"


@pytest.mark.parametrize("name", M2_NAMES)
def test_primitive_body_is_nonempty(name):
    assert primitive(name).body.strip(), \
        f"{name!r} primitive should have a non-empty assembly body"


@pytest.mark.parametrize("name", M2_NAMES)
def test_primitive_label_starts_with_underscore(name):
    label = primitive(name).label
    assert label.startswith("_"), \
        f"{name!r} primitive label {label!r} should follow Mach-O _-prefix convention"


def test_primitive_labels_are_unique():
    labels = [p.label for p in all_primitives()]
    assert len(set(labels)) == len(labels), \
        "every primitive must have a distinct asm label to avoid linker collisions"
