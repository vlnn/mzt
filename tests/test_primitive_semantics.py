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


import asm_runner
from asm_runner import assemble, STACK_BASE, STACK_SIZE


def _run_with_memory(asm_body, stack_in, mem_init):
    import unicorn
    from unicorn.arm64_const import UC_ARM64_REG_X19
    code = assemble(asm_body + "\n")
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(asm_runner.CODE_BASE, 4096)
    uc.mem_map(STACK_BASE, STACK_SIZE)
    uc.mem_write(asm_runner.CODE_BASE, code)
    for addr, val in mem_init.items():
        uc.mem_write(addr, (val & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little", signed=False))
    stack_top = STACK_BASE + STACK_SIZE
    initial_x19 = stack_top - 8 * len(stack_in)
    for offset, value in enumerate(reversed(stack_in)):
        uc.mem_write(initial_x19 + 8 * offset, (value & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little", signed=False))
    uc.reg_write(UC_ARM64_REG_X19, initial_x19)
    uc.emu_start(asm_runner.CODE_BASE, asm_runner.CODE_BASE + len(code))
    final_x19 = uc.reg_read(UC_ARM64_REG_X19)
    cells = []
    for addr in range(stack_top - 8, final_x19 - 1, -8):
        cells.append(int.from_bytes(uc.mem_read(addr, 8), "little", signed=True))
    return cells, uc


_WORK = STACK_BASE


@pytest.mark.parametrize("stored", [0, 1, 42, -7, 0x7FFFFFFFFFFFFFFF])
def test_fetch_returns_cell_at_address(stored):
    body = primitive("@").body
    cells, _ = _run_with_memory(body, [_WORK], {_WORK: stored})
    assert cells == [stored], \
        f"@ with addr containing {stored} should leave [{stored}] on stack, got {cells}"


@pytest.mark.parametrize("value", [0, 1, 42, -7])
def test_store_writes_cell_to_address(value):
    body = primitive("!").body
    cells, uc = _run_with_memory(body, [value, _WORK], {_WORK: 0})
    mem = int.from_bytes(uc.mem_read(_WORK, 8), "little", signed=True)
    assert cells == [], f"! should consume both operands; stack remained {cells}"
    assert mem == value, f"! should write {value} to memory; got {mem}"


def test_cfetch_returns_low_byte_zero_extended():
    body = primitive("c@").body
    cells, _ = _run_with_memory(body, [_WORK], {_WORK: 0xDEADBEEF})
    assert cells == [0xEF], \
        f"c@ should return zero-extended low byte (0xef), got {cells}"


def test_cstore_writes_low_byte_only():
    body = primitive("c!").body
    cells, uc = _run_with_memory(body, [0x12345678AB, _WORK], {_WORK: 0xAAAAAAAAAAAAAAAA})
    assert cells == [], f"c! should consume both operands; stack remained {cells}"
    raw = bytes(uc.mem_read(_WORK, 8))
    assert raw[0] == 0xAB, f"c! should overwrite the low byte with 0xab; got byte 0x{raw[0]:02x}"
    for i in range(1, 8):
        assert raw[i] == 0xAA, \
            f"c! must touch only the low byte; byte {i} changed to 0x{raw[i]:02x}"
