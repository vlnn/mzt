import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import Branch, Label, Literal, PrimRef


def _body(source: str):
    [d] = compile_source(source)
    return d.body


def _prim_calls(body):
    return [c.name for c in body if isinstance(c, PrimRef)]


# ---- basic do/loop ----

def test_do_loop_emits_setup_label_test_branch_label_unloop():
    body = _body(": main 5 0 do loop ;")
    assert any(isinstance(c, PrimRef) and c.name == "(do)" for c in body), \
        "do should emit a (do) primitive call to push limit/index onto rstack"
    assert any(isinstance(c, PrimRef) and c.name == "(loop)" for c in body), \
        "loop should emit a (loop) primitive call for increment+test"
    assert any(isinstance(c, PrimRef) and c.name == "unloop" for c in body), \
        "loop should emit unloop after the natural exit to drop rstack frames"


def test_do_loop_has_correct_cell_order():
    body = _body(": main 5 0 do loop ;")
    # Expected: Literal(5), Literal(0), PrimRef("(do)"), Label(N),
    #           PrimRef("(loop)"), Branch(target=N, conditional=True),
    #           Label(M), PrimRef("unloop")
    assert body[0] == Literal(5), "first cell should be the limit literal"
    assert body[1] == Literal(0), "second cell should be the start-index literal"
    assert body[2] == PrimRef("(do)"), "third cell is the (do) setup call"
    assert isinstance(body[3], Label), "fourth cell is the back-edge label"
    back_label_id = body[3].id
    # Body is empty, so loop test is next
    assert body[4] == PrimRef("(loop)"), "after the body, (loop) tests the index"
    assert body[5] == Branch(target=back_label_id, conditional=True), \
        "after (loop), conditional branch back on continue (cbz on the flag)"
    assert isinstance(body[6], Label), "exit label follows the back-branch"
    assert body[7] == PrimRef("unloop"), "unloop drops the rstack frame at exit"


def test_do_loop_with_body_keeps_body_inside_loop():
    body = _body(": main 5 0 do 42 loop ;")
    names = _prim_calls(body)
    # Body should contain (do), then a Literal(42) inside the loop, then (loop), unloop
    assert "(do)" in names and "(loop)" in names and "unloop" in names
    # Find the do and loop indices; literal 42 should be between
    do_idx = next(i for i, c in enumerate(body) if isinstance(c, PrimRef) and c.name == "(do)")
    loop_idx = next(i for i, c in enumerate(body) if isinstance(c, PrimRef) and c.name == "(loop)")
    inside = body[do_idx + 1 : loop_idx]
    assert Literal(42) in inside, \
        "literal inside do/loop should sit between the (do) call and the (loop) test"


# ---- +loop ----

def test_plus_loop_uses_plus_loop_test_primitive():
    body = _body(": main 10 0 do 2 +loop ;")
    names = _prim_calls(body)
    assert "(+loop)" in names, "+loop should emit a (+loop) primitive call"
    assert "(loop)" not in names, "+loop should NOT emit (loop) — distinct primitive"


# ---- leave ----

def test_leave_emits_unconditional_branch_to_loop_exit():
    body = _body(": main 10 0 do leave loop ;")
    branches = [c for c in body if isinstance(c, Branch)]
    unconditional = [b for b in branches if not b.conditional]
    assert unconditional, "leave should emit an unconditional branch (to the loop exit)"


def test_leave_outside_do_loop_raises():
    with pytest.raises(CompileError, match="leave"):
        compile_source(": main leave ;")


def test_leave_in_begin_loop_but_not_do_raises():
    with pytest.raises(CompileError, match="leave"):
        compile_source(": main begin leave again ;")


def test_two_leaves_both_branch_to_same_exit():
    body = _body(": main 10 0 do leave leave loop ;")
    unconditional = [c for c in body if isinstance(c, Branch) and not c.conditional]
    assert len(unconditional) == 2, \
        f"both leaves should produce unconditional branches; got {len(unconditional)}"
    targets = {b.target for b in unconditional}
    assert len(targets) == 1, \
        f"both leaves should branch to the same exit label; got distinct {targets}"


# ---- i and j scope checks ----

def test_i_outside_do_loop_raises():
    with pytest.raises(CompileError, match="'i'"):
        compile_source(": main i ;")


def test_j_outside_do_loop_raises():
    with pytest.raises(CompileError, match="'j'"):
        compile_source(": main j ;")


def test_defining_variable_named_i_rejected_as_primitive_collision():
    # i is registered as a primitive — defining `variable i` would shadow the
    # loop-index reader. Reject with a clear "primitive" message, not the
    # misleading "control-flow keyword" message.
    with pytest.raises(CompileError, match="primitive"):
        compile_source("variable i")


def test_defining_variable_named_j_rejected_as_primitive_collision():
    with pytest.raises(CompileError, match="primitive"):
        compile_source("variable j")


def test_array_sum_style_variable_idx_compiles():
    # The array-sum.fs pattern: a counter held in a variable named idx (NOT i).
    # This must still compile, since idx is not a reserved word.
    body_source = (
        "variable idx "
        ": main 0 idx ! begin idx @ 5 < while idx @ 1 + idx ! repeat ;"
    )
    [v, m] = compile_source(body_source)
    assert v.name == "idx", "first definition should be variable idx"
    assert m.name == "main", "second definition should be the main word"


def test_j_inside_single_do_loop_compiles_for_dynamic_outer_loop():
    body = _body(": foo 5 0 do j loop ;")
    assert PrimRef("j") in body, \
        "j inside a do-loop should compile — caller may provide the outer loop's frame at runtime"


def test_i_inside_do_loop_compiles():
    body = _body(": main 10 0 do i loop ;")
    assert PrimRef("i") in body, "i inside do/loop should compile to PrimRef('i')"


def test_j_inside_nested_do_loops_compiles():
    body = _body(": main 5 0 do 3 0 do j i loop loop ;")
    assert PrimRef("i") in body and PrimRef("j") in body, \
        "j inside doubly-nested do/loop should compile cleanly"


# ---- malformed control flow ----

@pytest.mark.parametrize(
    "source,fragment",
    [
        (": main loop ;",            "without matching"),
        (": main do 5 ;",            "unclosed control flow"),
        (": main 5 0 +loop ;",       "without matching"),
    ],
)
def test_malformed_do_loop_raises(source, fragment):
    with pytest.raises(CompileError, match=fragment):
        compile_source(source)


# ---- nesting and label uniqueness ----

def test_nested_do_loops_get_distinct_labels():
    body = _body(": main 5 0 do 3 0 do loop loop ;")
    labels = [c.id for c in body if isinstance(c, Label)]
    assert len(labels) == len(set(labels)), \
        f"nested do/loops should have distinct label IDs; got {labels}"


def test_do_loop_inside_if_compiles():
    body = _body(": main 1 if 5 0 do loop then ;")
    assert PrimRef("(do)") in body and PrimRef("(loop)") in body, \
        "do/loop inside if/then should still compile cleanly"


def test_nested_loops_emit_two_pairs_of_do_and_loop():
    body = _body(": main 5 0 do 3 0 do loop loop ;")
    do_count = sum(1 for c in body if isinstance(c, PrimRef) and c.name == "(do)")
    loop_count = sum(1 for c in body if isinstance(c, PrimRef) and c.name == "(loop)")
    unloop_count = sum(1 for c in body if isinstance(c, PrimRef) and c.name == "unloop")
    assert do_count == 2 and loop_count == 2 and unloop_count == 2, \
        f"two nested loops should each produce one (do)/(loop)/unloop trio; " \
        f"got do={do_count}, loop={loop_count}, unloop={unloop_count}"


# ---- r_depth interaction ----

def test_user_to_r_inside_do_must_balance_before_loop():
    # User pushes >r inside body but doesn't pop before loop — depth stays unbalanced.
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": main 5 0 do 42 >r loop ;")


def test_user_to_r_balanced_inside_do_compiles():
    body = _body(": main 5 0 do 42 >r r> drop loop ;")
    assert PrimRef("(do)") in body, \
        "balanced >r/r> inside do/loop body should compile"


def test_leave_with_unbalanced_user_to_r_raises():
    with pytest.raises(CompileError, match="return stack"):
        compile_source(": main 5 0 do 42 >r leave loop ;")
