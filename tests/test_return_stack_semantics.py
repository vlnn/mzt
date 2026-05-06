import pytest

import asm_runner
from asm_runner import run_with_stacks
from mzt.primitives import primitive


pytestmark = pytest.mark.skipif(
    not asm_runner.HARNESS_AVAILABLE,
    reason=f"primitive harness unavailable: {asm_runner.HARNESS_ERROR}",
)


@pytest.mark.parametrize("value", [0, 1, 42, -7, 0x7FFFFFFFFFFFFFFF])
def test_to_r_moves_top_of_data_stack_onto_return_stack(value):
    body = primitive(">r").body
    dstack, rstack = run_with_stacks(body, dstack_in=[value], rstack_in=[])
    assert dstack == [], \
        f">r should pop the data stack; got {dstack}"
    assert rstack == [value], \
        f">r should push {value} onto the return stack; got {rstack}"


@pytest.mark.parametrize("value", [0, 1, 42, -7])
def test_r_from_moves_top_of_return_stack_onto_data_stack(value):
    body = primitive("r>").body
    dstack, rstack = run_with_stacks(body, dstack_in=[], rstack_in=[value])
    assert dstack == [value], \
        f"r> should push {value} onto the data stack; got {dstack}"
    assert rstack == [], \
        f"r> should pop the return stack; got {rstack}"


@pytest.mark.parametrize("value", [0, 1, 42, -7])
def test_r_fetch_copies_top_of_return_stack_onto_data_stack(value):
    body = primitive("r@").body
    dstack, rstack = run_with_stacks(body, dstack_in=[], rstack_in=[value])
    assert dstack == [value], \
        f"r@ should push {value} onto the data stack; got {dstack}"
    assert rstack == [value], \
        f"r@ should not consume the return stack; got {rstack}"


def test_to_r_then_r_from_round_trips_a_value():
    asm = primitive(">r").body + primitive("r>").body
    dstack, rstack = run_with_stacks(asm, dstack_in=[123], rstack_in=[])
    assert dstack == [123], \
        f">r r> should be a round-trip on the data stack; got {dstack}"
    assert rstack == [], \
        f">r r> should leave the return stack as it was; got {rstack}"


def test_to_r_preserves_data_stack_below_top():
    sentinel = 0x0BADBADC0FFEE
    body = primitive(">r").body
    dstack, _ = run_with_stacks(body, dstack_in=[sentinel, 42], rstack_in=[])
    assert dstack == [sentinel], \
        f">r must not disturb cells beneath the top; got {dstack}"


def test_r_from_preserves_return_stack_below_top():
    sentinel = 0x0BADBADC0FFEE
    body = primitive("r>").body
    _, rstack = run_with_stacks(body, dstack_in=[], rstack_in=[sentinel, 42])
    assert rstack == [sentinel], \
        f"r> must not disturb the return stack beneath the top; got {rstack}"


def test_r_fetch_with_two_cells_only_reads_the_top():
    body = primitive("r@").body
    dstack, rstack = run_with_stacks(body, dstack_in=[], rstack_in=[99, 7])
    assert dstack == [7], \
        f"r@ should copy only the topmost return-stack cell (7); got {dstack}"
    assert rstack == [99, 7], \
        f"r@ must leave the return stack unchanged; got {rstack}"


def test_two_to_r_reverse_order_on_return_stack():
    body = primitive(">r").body + primitive(">r").body
    dstack, rstack = run_with_stacks(body, dstack_in=[1, 2], rstack_in=[])
    assert dstack == [], \
        f"two >r should empty the input data stack; got {dstack}"
    assert rstack == [2, 1], \
        f"two >r reverses order: 2 (data top) is pushed first, then 1; got {rstack}"
