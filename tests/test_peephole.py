import pytest

from mzt.ir import Branch, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit
from mzt.peephole import all_rules, optimize, optimize_body


def test_empty_body_passes_through():
    assert optimize_body(()) == (), \
        "empty body should optimize to empty body"


def test_body_with_no_matches_is_unchanged():
    body = (Literal(7), PrimRef("dup"), PrimRef("+"))
    assert optimize_body(body) == body, \
        "bodies with no rule matches should round-trip unchanged"


def test_literal_zero_becomes_zero_primitive():
    assert optimize_body((Literal(0),)) == (PrimRef("zero"),), \
        "Literal(0) should be replaced by PrimRef('zero')"


def test_nonzero_literals_are_not_touched():
    body = (Literal(1), Literal(-1), Literal(42))
    assert optimize_body(body) == body, \
        "the zero-push rule must only fire for Literal(0), not other integers"


def test_swap_drop_fuses_to_nip():
    assert optimize_body((PrimRef("swap"), PrimRef("drop"))) == (PrimRef("nip"),), \
        "consecutive swap+drop should fuse into a single nip"


def test_swap_followed_by_other_word_is_unchanged():
    body = (PrimRef("swap"), PrimRef("dup"))
    assert optimize_body(body) == body, \
        "swap should only fuse when immediately followed by drop"


@pytest.mark.parametrize(
    "body,expected",
    [
        ((Literal(0), Literal(0)),
         (PrimRef("zero"), PrimRef("zero"))),
        ((Literal(0), PrimRef("dup"), Literal(0)),
         (PrimRef("zero"), PrimRef("dup"), PrimRef("zero"))),
        ((PrimRef("swap"), PrimRef("drop"), PrimRef("swap"), PrimRef("drop")),
         (PrimRef("nip"), PrimRef("nip"))),
    ],
)
def test_rule_fires_at_every_matching_position(body, expected):
    assert optimize_body(body) == expected, \
        f"every match in {body} should be replaced, got {optimize_body(body)}"


def test_rules_cascade_zero_inside_swap_drop():
    body = (Literal(0), PrimRef("swap"), PrimRef("drop"))
    assert optimize_body(body) == (PrimRef("zero"), PrimRef("nip")), \
        "both rules should fire in the same body"


def test_optimization_is_idempotent():
    body = (Literal(0), PrimRef("swap"), PrimRef("drop"), Literal(0))
    once = optimize_body(body)
    twice = optimize_body(once)
    assert once == twice, \
        "running peephole twice should yield the same result as running it once"


def test_control_flow_cells_are_left_alone():
    body = (Label(0), Literal(0), Branch(target=0, conditional=True))
    out = optimize_body(body)
    assert out == (Label(0), PrimRef("zero"), Branch(target=0, conditional=True)), \
        "labels and branches should be preserved; only matched runs are rewritten"


def test_string_lit_is_left_alone():
    body = (StringLit("hi"), Literal(0))
    assert optimize_body(body) == (StringLit("hi"), PrimRef("zero")), \
        "StringLit cells should pass through peephole unchanged"


def test_optimize_processes_each_colon_def():
    defs = [
        ColonDef("a", (Literal(0),)),
        ColonDef("b", (PrimRef("swap"), PrimRef("drop"))),
    ]
    optimized = optimize(defs)
    assert optimized[0].body == (PrimRef("zero"),), \
        "first def should have its zero-push optimized"
    assert optimized[1].body == (PrimRef("nip"),), \
        "second def should have its swap-drop fused"


def test_optimize_preserves_def_names():
    defs = [ColonDef("foo", (Literal(0),))]
    assert optimize(defs)[0].name == "foo", \
        "optimization must not change colon definition names"


def test_rules_registry_contains_seed_rules():
    names = {r.name for r in all_rules()}
    assert "zero-push" in names, "the Literal(0) -> zero rule must be registered"
    assert "swap-drop-as-nip" in names, "the swap+drop -> nip rule must be registered"


def test_longer_patterns_win_over_shorter_ones():
    body = (PrimRef("swap"), PrimRef("drop"))
    out = optimize_body(body)
    assert out == (PrimRef("nip"),), \
        "two-cell swap+drop pattern must win even if a one-cell rule could match a sub-cell"
