import pytest

import asm_runner
from asm_runner import run_primitive
from mzt.primitives import primitive


pytestmark = pytest.mark.skipif(
    not asm_runner.HARNESS_AVAILABLE,
    reason=f"primitive harness unavailable: {asm_runner.HARNESS_ERROR}",
)


CASES = [
    ("dup",    [42],            [42, 42]),
    ("dup",    [1, 2],          [1, 2, 2]),
    ("dup",    [-5],            [-5, -5]),

    ("drop",   [1, 2],          [1]),
    ("drop",   [1, 2, 3],       [1, 2]),

    ("swap",   [1, 2],          [2, 1]),
    ("swap",   [99, 1, 2],      [99, 2, 1]),
    ("swap",   [-3, 7],         [7, -3]),

    ("over",   [1, 2],          [1, 2, 1]),
    ("over",   [99, 1, 2],      [99, 1, 2, 1]),

    ("nip",    [1, 2],          [2]),
    ("nip",    [99, 1, 2],      [99, 2]),

    ("rot",    [1, 2, 3],       [2, 3, 1]),
    ("rot",    [99, 1, 2, 3],   [99, 2, 3, 1]),

    ("+",      [2, 3],          [5]),
    ("+",      [-1, 1],         [0]),
    ("+",      [10, 20, 30],    [10, 50]),

    ("-",      [10, 3],         [7]),
    ("-",      [3, 10],         [-7]),
    ("-",      [0, 0],          [0]),

    ("*",      [3, 4],          [12]),
    ("*",      [-2, 5],         [-10]),
    ("*",      [0, 99],         [0]),

    ("/mod",   [10, 3],         [1, 3]),
    ("/mod",   [9, 3],          [0, 3]),
    ("/mod",   [-7, 2],         [-1, -3]),
    ("/mod",   [7, -2],         [1, -3]),

    ("=",      [5, 5],          [-1]),
    ("=",      [5, 6],          [0]),
    ("=",      [-1, -1],        [-1]),

    ("<",      [3, 5],          [-1]),
    ("<",      [5, 3],          [0]),
    ("<",      [5, 5],          [0]),
    ("<",      [-1, 0],         [-1]),

    (">",      [5, 3],          [-1]),
    (">",      [3, 5],          [0]),
    (">",      [5, 5],          [0]),

    ("0=",     [0],             [-1]),
    ("0=",     [5],             [0]),
    ("0=",     [-1],            [0]),

    ("and",    [0b1100, 0b1010], [0b1000]),
    ("and",    [-1, 42],         [42]),

    ("or",     [0b1100, 0b1010], [0b1110]),
    ("or",     [0, 42],          [42]),

    ("xor",    [0b1100, 0b1010], [0b0110]),
    ("xor",    [42, 42],         [0]),

    ("invert", [0],             [-1]),
    ("invert", [-1],            [0]),
    ("invert", [42],            [~42]),

    ("negate", [5],             [-5]),
    ("negate", [-3],            [3]),
    ("negate", [0],              [0]),

    ("abs",    [-7],            [7]),
    ("abs",    [7],             [7]),
    ("abs",    [0],             [0]),
]


def _case_id(case):
    name, stack_in, stack_out = case
    return f"{name}({stack_in}->{stack_out})"


@pytest.mark.parametrize(
    "name,stack_in,stack_out",
    CASES,
    ids=[_case_id(c) for c in CASES],
)
def test_primitive_behavior(name, stack_in, stack_out):
    body = primitive(name).body
    actual = run_primitive(body, stack_in)
    assert actual == stack_out, \
        f"{name!r} on stack {stack_in} should yield {stack_out}, got {actual}"


@pytest.mark.parametrize(
    "name",
    ["dup", "drop", "swap", "over", "nip", "rot",
     "+", "-", "*", "and", "or", "xor",
     "invert", "negate", "abs", "0=", "=", "<", ">"],
)
def test_primitive_preserves_deep_stack(name):
    sentinel = 0x0BADBADC0FFEE
    depth_needed = {
        "dup": 1, "drop": 1, "0=": 1, "invert": 1, "negate": 1, "abs": 1,
        "swap": 2, "over": 2, "nip": 2,
        "+": 2, "-": 2, "*": 2,
        "and": 2, "or": 2, "xor": 2,
        "=": 2, "<": 2, ">": 2,
        "rot": 3,
    }[name]
    filler = [sentinel] + list(range(depth_needed))

    body = primitive(name).body
    result = run_primitive(body, filler)

    assert result[0] == sentinel, \
        f"{name!r} should not disturb stack cells beneath its documented depth"
