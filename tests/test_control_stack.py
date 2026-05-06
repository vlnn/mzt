import pytest

from mzt.control_stack import ControlStack, ControlStackError


def test_new_stack_is_falsy_and_empty():
    cs = ControlStack()
    assert not cs, "a fresh control stack should be falsy"
    assert len(cs) == 0, "a fresh control stack should report length 0"


def test_push_then_len_and_truthy():
    cs = ControlStack()
    cs.push("orig", 7)
    assert len(cs) == 1, "after one push len should be 1"
    assert cs, "a non-empty control stack should be truthy"


def test_pop_returns_value_and_shrinks():
    cs = ControlStack()
    cs.push("orig", 42)
    value = cs.pop("orig")
    assert value == 42, "pop should return the value associated with the matching tag"
    assert len(cs) == 0, "pop should remove the frame"


def test_pop_with_wrong_tag_raises_with_helpful_message():
    cs = ControlStack()
    cs.push("dest", 3)
    with pytest.raises(ControlStackError, match="expected orig.*got dest"):
        cs.pop("orig")


def test_pop_from_empty_raises_with_context():
    cs = ControlStack()
    with pytest.raises(ControlStackError, match="underflow.*orig"):
        cs.pop("orig")


def test_pop_any_accepts_either_tag():
    cs = ControlStack()
    cs.push("dest", 9)
    tag, value = cs.pop_any(["orig", "dest"])
    assert (tag, value) == ("dest", 9), \
        "pop_any should return both the tag and the value of whichever frame matched"


def test_pop_any_with_no_match_raises():
    cs = ControlStack()
    cs.push("do", 1)
    with pytest.raises(ControlStackError, match="orig/dest.*do"):
        cs.pop_any(["orig", "dest"])


def test_peek_returns_top_without_removing():
    cs = ControlStack()
    cs.push("orig", 5)
    cs.push("dest", 11)
    assert cs.peek() == ("dest", 11), "peek should return the most recently pushed frame"
    assert len(cs) == 2, "peek should not remove the frame"


def test_peek_on_empty_raises():
    with pytest.raises(ControlStackError, match="underflow"):
        ControlStack().peek()


def test_find_innermost_skips_intervening_frames():
    cs = ControlStack()
    cs.push("do", 1)
    cs.push("orig", 2)
    cs.push("orig", 3)
    found = cs.find_innermost("do")
    assert found == ("do", 1), \
        "find_innermost should walk back through inner frames to find the matching tag"


def test_find_innermost_returns_none_when_absent():
    cs = ControlStack()
    cs.push("orig", 1)
    assert cs.find_innermost("do") is None, \
        "find_innermost should return None when no frame carries the requested tag"


def test_find_innermost_returns_nearest_when_multiple_match():
    cs = ControlStack()
    cs.push("do", 1)
    cs.push("do", 2)
    cs.push("orig", 99)
    assert cs.find_innermost("do") == ("do", 2), \
        "find_innermost should return the nearest matching frame, not the outermost"


def test_iter_visits_frames_in_push_order():
    cs = ControlStack()
    cs.push("a", 1)
    cs.push("b", 2)
    cs.push("c", 3)
    assert list(cs) == [("a", 1), ("b", 2), ("c", 3)], \
        "iteration should yield frames bottom-to-top in push order"


def test_clear_empties_the_stack():
    cs = ControlStack()
    cs.push("a", 1)
    cs.push("b", 2)
    cs.clear()
    assert len(cs) == 0, "clear should remove every frame"
