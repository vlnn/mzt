import pytest

import asm_runner
from asm_runner import run_with_stacks
from mzt.primitives import primitive


pytestmark = pytest.mark.skipif(
    not asm_runner.HARNESS_AVAILABLE,
    reason=f"primitive harness unavailable: {asm_runner.HARNESS_ERROR}",
)


# (do) ( limit index -- ) — pushes limit, then index onto rstack
# Net effect: rstack ends up ( ... limit index ) with index on top.

def test_do_init_pushes_limit_then_index_with_index_on_top():
    body = primitive("(do)").body
    dstack, rstack = run_with_stacks(body, dstack_in=[10, 3], rstack_in=[])
    assert dstack == [], \
        "(do) should consume both data-stack operands"
    assert rstack == [10, 3], \
        f"(do) with ( limit=10 index=3 ) should produce rstack ( 10 3 ); got {rstack}"


def test_do_init_does_not_disturb_existing_rstack():
    sentinel = 0x0BADC0FFEE
    body = primitive("(do)").body
    _, rstack = run_with_stacks(body, dstack_in=[5, 0], rstack_in=[sentinel])
    assert rstack == [sentinel, 5, 0], \
        f"(do) should push above existing rstack; got {rstack}"


@pytest.mark.parametrize(
    "limit,index",
    [(10, 0), (5, 5), (0, -3), (-1, -10)],
)
def test_do_init_signed_values(limit, index):
    body = primitive("(do)").body
    _, rstack = run_with_stacks(body, dstack_in=[limit, index], rstack_in=[])
    assert rstack == [limit, index], \
        f"(do) with ( {limit} {index} ) should produce rstack ( {limit} {index} )"


# (loop) — increments index; pushes -1 to dstack if done, 0 if continue.

@pytest.mark.parametrize(
    "index_before,limit,expected_index_after,expected_flag",
    [
        # natural increment, not yet at limit
        (0, 5, 1, 0),
        (3, 5, 4, 0),
        # last iteration: increment makes index == limit
        (4, 5, 5, -1),
        # signed: from -2 to -1 below limit 0
        (-2, 0, -1, 0),
        # signed: from -1 to 0, equals limit, done
        (-1, 0, 0, -1),
    ],
)
def test_loop_test_increments_and_compares(index_before, limit, expected_index_after, expected_flag):
    body = primitive("(loop)").body
    dstack, rstack = run_with_stacks(
        body, dstack_in=[], rstack_in=[limit, index_before]
    )
    assert dstack == [expected_flag], \
        f"(loop) with index={index_before} limit={limit} should push flag {expected_flag}, got {dstack}"
    assert rstack == [limit, expected_index_after], \
        f"(loop) should write incremented index back; expected rstack [{limit}, {expected_index_after}], got {rstack}"


# (+loop) ( step -- flag ) — applies step, tests crossing limit-(limit-1) boundary.

@pytest.mark.parametrize(
    "index_before,limit,step,expected_index_after,expected_flag,description",
    [
        # step=1: same as (loop) for cross detection
        (3, 5, 1, 4, 0, "step=1 not yet at limit"),
        (4, 5, 1, 5, -1, "step=1 reaches limit"),
        # step=2: cross from 4→6 over limit 5
        (3, 5, 2, 5, -1, "step=2 lands on limit"),
        (2, 5, 2, 4, 0, "step=2 lands below limit"),
        (4, 5, 2, 6, -1, "step=2 crosses past limit"),
        # negative step: counting down
        (5, 0, -1, 4, 0, "step=-1 going from 5 toward 0"),
        (1, 0, -1, 0, 0, "step=-1 from 1 to limit — not yet crossing boundary at -1/0"),
        (0, 0, -1, -1, -1, "step=-1 from 0 to -1 — crosses below limit"),
        # large positive step that overshoots
        (3, 5, 10, 13, -1, "step=10 overshoots dramatically"),
    ],
)
def test_plus_loop_test_handles_signed_step_and_crossing(
    index_before, limit, step, expected_index_after, expected_flag, description,
):
    body = primitive("(+loop)").body
    dstack, rstack = run_with_stacks(
        body, dstack_in=[step], rstack_in=[limit, index_before]
    )
    assert dstack == [expected_flag], \
        f"(+loop) [{description}]: idx={index_before}, limit={limit}, step={step} → " \
        f"flag {expected_flag}, got {dstack}"
    assert rstack == [limit, expected_index_after], \
        f"(+loop) [{description}]: expected rstack [{limit}, {expected_index_after}], got {rstack}"


# unloop — drops limit and index from rstack.

def test_unloop_drops_two_cells_from_rstack():
    body = primitive("unloop").body
    dstack, rstack = run_with_stacks(
        body, dstack_in=[], rstack_in=[99, 5, 3]
    )
    assert dstack == [], \
        "unloop should not touch the data stack"
    assert rstack == [99], \
        f"unloop should drop the top two cells (limit, index); got {rstack}"


def test_unloop_with_exactly_two_cells_empties_rstack():
    body = primitive("unloop").body
    _, rstack = run_with_stacks(body, dstack_in=[], rstack_in=[5, 3])
    assert rstack == [], \
        f"unloop on ( limit index ) should empty the rstack; got {rstack}"


# i — copy top of rstack onto dstack.

@pytest.mark.parametrize("limit,index", [(5, 0), (10, 3), (0, -5)])
def test_i_copies_top_of_rstack(limit, index):
    body = primitive("i").body
    dstack, rstack = run_with_stacks(
        body, dstack_in=[], rstack_in=[limit, index]
    )
    assert dstack == [index], \
        f"i should copy the loop index ({index}) onto data stack; got {dstack}"
    assert rstack == [limit, index], \
        f"i must not consume the rstack; got {rstack}"


# j — copy fourth-from-top of rstack onto dstack (skips current loop's pair).

def test_j_reads_outer_loop_index_at_offset_16():
    body = primitive("j").body
    outer_limit, outer_idx = 100, 7
    inner_limit, inner_idx = 5, 2
    dstack, rstack = run_with_stacks(
        body, dstack_in=[],
        rstack_in=[outer_limit, outer_idx, inner_limit, inner_idx],
    )
    assert dstack == [outer_idx], \
        f"j should read the outer loop's index ({outer_idx}); got {dstack}"
    assert rstack == [outer_limit, outer_idx, inner_limit, inner_idx], \
        f"j must not disturb the rstack; got {rstack}"


# Integration: do + body + loop should end with rstack empty and correct iteration count.

def test_do_loop_iteration_count_via_composed_primitives():
    # Simulate `5 0 do <noop> loop` — should iterate 5 times and end with empty rstack.
    do_init = primitive("(do)").body
    loop_test = primitive("(loop)").body

    # Build: (do) for setup, then loop until done.
    # We can't include an unconditional branch in raw asm without labels easily,
    # so instead we test in pieces:
    # 1. Run (do) with [5, 0] → rstack [5, 0]
    dstack, rstack = run_with_stacks(do_init, dstack_in=[5, 0], rstack_in=[])
    assert rstack == [5, 0], \
        f"(do) setup should produce rstack [5, 0]; got {rstack}"

    # 2. Manually iterate: each (loop) call increments index and pushes flag.
    iterations = 0
    while True:
        dstack, rstack = run_with_stacks(
            loop_test, dstack_in=[], rstack_in=rstack
        )
        iterations += 1
        flag = dstack[0]
        if flag == -1:
            break
    assert iterations == 5, \
        f"loop with limit=5, start=0 should iterate exactly 5 times; got {iterations}"
    assert rstack[1] == 5, \
        f"after final loop, index should equal limit (5); got {rstack[1]}"
