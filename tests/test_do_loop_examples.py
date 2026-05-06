from pathlib import Path

import pytest

from mzt.builder import compile_to_asm


EXAMPLES = Path(__file__).parent.parent / "examples"


DO_LOOP_FILES = ["do-count.fs", "do-sum.fs", "do-leave.fs", "do-nested.fs"]


@pytest.mark.parametrize("source_name", DO_LOOP_FILES)
def test_do_loop_example_compiles(source_name):
    source = (EXAMPLES / source_name).read_text()
    asm = compile_to_asm(source)
    assert "_word_main:" in asm, \
        f"{source_name} should compile and produce a _word_main entry point"


@pytest.mark.parametrize("source_name", DO_LOOP_FILES)
def test_do_loop_example_emits_do_init_and_unloop(source_name):
    asm = compile_to_asm((EXAMPLES / source_name).read_text())
    assert "bl      _do_init" in asm, \
        f"{source_name} should emit a (do) call to push limit/index onto rstack"
    assert "bl      _unloop" in asm, \
        f"{source_name} should emit an unloop after the loop body to clean up rstack"


def test_do_count_emits_loop_test_and_loop_i():
    asm = compile_to_asm((EXAMPLES / "do-count.fs").read_text())
    for needle in ("bl      _loop_test", "bl      _loop_i"):
        assert needle in asm, \
            f"do-count.fs should emit {needle!r} (uses (loop) and i)"


def test_do_sum_emits_loop_test_and_one_plus():
    asm = compile_to_asm((EXAMPLES / "do-sum.fs").read_text())
    for needle in ("bl      _loop_test", "bl      _one_plus", "bl      _loop_i", "bl      _plus"):
        assert needle in asm, \
            f"do-sum.fs should emit {needle!r}"


def test_do_leave_has_two_branches_one_back_one_forward():
    asm = compile_to_asm((EXAMPLES / "do-leave.fs").read_text())
    cbz_count = asm.count("cbz     x0, L")
    b_count = sum(
        1 for line in asm.split("\n")
        if line.strip().startswith("b       L")
    )
    assert cbz_count >= 2, \
        f"do-leave.fs should have at least 2 cbz branches (loop back-edge + if test); got {cbz_count}"
    assert b_count >= 1, \
        f"do-leave.fs should emit at least one unconditional branch (the leave); got {b_count}"


def test_do_nested_emits_loop_j_for_outer_index_access():
    asm = compile_to_asm((EXAMPLES / "do-nested.fs").read_text())
    assert "bl      _loop_j" in asm, \
        "do-nested.fs should emit a bl _loop_j call (j accesses outer-loop index)"
    assert "bl      _loop_i" in asm, \
        "do-nested.fs should also emit bl _loop_i (i accesses inner-loop index)"


def test_do_nested_emits_two_do_init_calls():
    asm = compile_to_asm((EXAMPLES / "do-nested.fs").read_text())
    do_init_count = asm.count("bl      _do_init")
    assert do_init_count == 2, \
        f"do-nested.fs has two do/loop pairs across two colon definitions; " \
        f"should emit 2 bl _do_init calls, got {do_init_count}"
