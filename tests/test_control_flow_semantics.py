import pytest

from asm_runner import HARNESS_AVAILABLE, HARNESS_ERROR, run_primitive


pytestmark = pytest.mark.skipif(
    not HARNESS_AVAILABLE,
    reason=f"primitive harness unavailable: {HARNESS_ERROR}",
)


def _push(value: int) -> str:
    return f"    mov     x0, #{value}\n    str     x0, [x19, #-8]!\n"


def _branch_if_zero(target: str) -> str:
    return f"    ldr     x0, [x19], #8\n    cbz     x0, {target}\n"


def _branch(target: str) -> str:
    return f"    b       {target}\n"


@pytest.mark.parametrize(
    "flag,expected",
    [(0, []), (1, [42]), (-1, [42]), (999, [42])],
)
def test_if_then_executes_body_only_when_flag_is_nonzero(flag, expected):
    body = (
        _push(flag)
        + _branch_if_zero("L0")
        + _push(42)
        + "L0:\n"
    )
    assert run_primitive(body, []) == expected, \
        f"if-then with flag {flag} should leave {expected} on the stack"


@pytest.mark.parametrize(
    "flag,expected",
    [(0, [22]), (1, [11]), (-1, [11]), (7, [11])],
)
def test_if_else_then_picks_branch_by_flag(flag, expected):
    body = (
        _push(flag)
        + _branch_if_zero("L0")
        + _push(11)
        + _branch("L1")
        + "L0:\n"
        + _push(22)
        + "L1:\n"
    )
    assert run_primitive(body, []) == expected, \
        f"if-else with flag {flag} should leave {expected} on the stack"


def test_unconditional_branch_skips_subsequent_code():
    body = (
        _push(1)
        + _branch("L0")
        + _push(99)
        + "L0:\n"
        + _push(2)
    )
    assert run_primitive(body, []) == [1, 2], \
        "unconditional branch should skip the 99 push and land on the label"


def test_begin_until_loop_runs_until_flag_becomes_nonzero():
    body = (
        _push(3)
        + "Lstart:\n"
        + "    ldr     x0, [x19]\n"
        + "    sub     x0, x0, #1\n"
        + "    str     x0, [x19]\n"
        + "    ldr     x0, [x19]\n"
        + "    cmp     x0, #0\n"
        + "    csetm   x0, eq\n"
        + "    str     x0, [x19, #-8]!\n"
        + _branch_if_zero("Lstart")
    )
    assert run_primitive(body, []) == [0], \
        "begin/until-style loop should leave the counter at 0 after the flag turns true"


def test_nested_if_else_branches_to_inner_then_outer():
    body = (
        _push(1)
        + _branch_if_zero("Louter_else")
        + _push(0)
        + _branch_if_zero("Linner_else")
        + _push(11)
        + _branch("Linner_end")
        + "Linner_else:\n"
        + _push(22)
        + "Linner_end:\n"
        + _branch("Louter_end")
        + "Louter_else:\n"
        + _push(33)
        + "Louter_end:\n"
    )
    assert run_primitive(body, []) == [22], \
        "nested if/else with outer=true, inner=false should pick the inner else (22)"
