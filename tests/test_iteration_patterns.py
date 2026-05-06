from pathlib import Path

import pytest

from mzt.builder import compile_to_asm


EXAMPLES = Path(__file__).parent.parent / "examples"


REGRESS_FILES = [
    "regress-iter-countdown.fs",
    "regress-iter-sum.fs",
    "regress-iter-search.fs",
]


@pytest.mark.parametrize("source_name", REGRESS_FILES)
def test_iteration_pattern_compiles(source_name):
    source = (EXAMPLES / source_name).read_text()
    asm = compile_to_asm(source)
    assert asm, f"{source_name} should compile to non-empty assembly"
    assert "_word_main:" in asm, \
        f"{source_name} should produce a main entry point in the emitted asm"


def test_countdown_pattern_emits_one_minus_call():
    asm = compile_to_asm((EXAMPLES / "regress-iter-countdown.fs").read_text())
    assert "bl      _one_minus" in asm, \
        "the countdown pattern should compile '1-' to a bl _one_minus call"


def test_sum_pattern_emits_one_minus_and_return_stack_calls():
    asm = compile_to_asm((EXAMPLES / "regress-iter-sum.fs").read_text())
    for needle in ("bl      _one_minus", "bl      _to_r", "bl      _r_from"):
        assert needle in asm, \
            f"the sum pattern should emit {needle!r} (uses 1- plus >r/r> stash)"


def test_search_pattern_emits_one_plus_call():
    asm = compile_to_asm((EXAMPLES / "regress-iter-search.fs").read_text())
    assert "bl      _one_plus" in asm, \
        "the bounded-search pattern should compile '1+' to a bl _one_plus call"


@pytest.mark.parametrize(
    "source_name,must_contain",
    [
        ("regress-iter-countdown.fs", "begin"),
        ("regress-iter-sum.fs",       "begin"),
        ("regress-iter-search.fs",    "begin"),
    ],
)
def test_iteration_examples_use_only_existing_loop_constructs(source_name, must_contain):
    source = (EXAMPLES / source_name).read_text()
    assert must_contain in source, \
        f"{source_name} should use the existing M3 begin-style loops, " \
        f"not constructs reserved for step 3 (do/loop)"
    for forbidden in (" do ", " loop ", " +loop ", " leave ", " i ", " j "):
        assert forbidden not in source, \
            f"{source_name} must not use {forbidden.strip()!r} — those land in step 3, " \
            "and these examples are precisely the baseline that step 3 will replace"
