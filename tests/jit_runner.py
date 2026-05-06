try:
    import unicorn
    from unicorn.arm64_const import (
        UC_ARM64_REG_LR,
        UC_ARM64_REG_SP,
        UC_ARM64_REG_X19,
        UC_ARM64_REG_X20,
    )
    AVAILABLE = True
    UNAVAILABLE_REASON = None
except ImportError as exc:
    AVAILABLE = False
    UNAVAILABLE_REASON = f"unicorn not importable: {exc!r}"


JIT_BASE = 0x1000_0000
PRIM_BASE = 0x4000_0000
DSTACK_BASE = 0x2000_0000
DSTACK_SIZE = 0x1000
RSTACK_BASE = 0x3000_0000
RSTACK_SIZE = 0x1000
HOST_STACK_BASE = 0x5000_0000
HOST_STACK_SIZE = 0x1000

SENTINEL_LR = 0x0F0F_0F0F_0000


def _round_up(value: int, page: int = 0x1000) -> int:
    return (value + page - 1) & ~(page - 1)


def run_jit_body(
    jit_bytes: bytes,
    primitive_stubs: dict[int, bytes] | None = None,
    dstack_in: list[int] | None = None,
    rstack_in: list[int] | None = None,
) -> list[int]:
    if not AVAILABLE:
        raise RuntimeError(UNAVAILABLE_REASON)
    primitive_stubs = primitive_stubs or {}
    dstack_in = dstack_in or []
    rstack_in = rstack_in or []

    uc = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_LITTLE_ENDIAN)

    uc.mem_map(JIT_BASE, _round_up(len(jit_bytes)))
    uc.mem_write(JIT_BASE, jit_bytes)

    _map_primitive_stubs(uc, primitive_stubs)

    uc.mem_map(DSTACK_BASE, DSTACK_SIZE)
    uc.mem_map(RSTACK_BASE, RSTACK_SIZE)
    uc.mem_map(HOST_STACK_BASE, HOST_STACK_SIZE)

    dstack_top = DSTACK_BASE + DSTACK_SIZE
    x19 = _push_initial_stack(uc, dstack_top, dstack_in)
    rstack_top = RSTACK_BASE + RSTACK_SIZE
    x20 = _push_initial_stack(uc, rstack_top, rstack_in)

    uc.reg_write(UC_ARM64_REG_X19, x19)
    uc.reg_write(UC_ARM64_REG_X20, x20)
    uc.reg_write(UC_ARM64_REG_SP, HOST_STACK_BASE + HOST_STACK_SIZE - 16)
    uc.reg_write(UC_ARM64_REG_LR, SENTINEL_LR)

    try:
        uc.emu_start(JIT_BASE, SENTINEL_LR)
    except unicorn.UcError:
        pass

    return _read_dstack(uc, uc.reg_read(UC_ARM64_REG_X19), dstack_top)


def _map_primitive_stubs(uc, stubs: dict[int, bytes]) -> None:
    pages: dict[int, int] = {}
    for addr, body in stubs.items():
        page = addr & ~0xFFF
        end = _round_up(addr + len(body))
        size = end - page
        pages[page] = max(pages.get(page, 0), size)
    for page, size in pages.items():
        uc.mem_map(page, size)
    for addr, body in stubs.items():
        uc.mem_write(addr, body)


def _push_initial_stack(uc, top: int, values: list[int]) -> int:
    pointer = top
    for value in values:
        pointer -= 8
        uc.mem_write(pointer, _to_signed_bytes(value))
    return pointer


def _to_signed_bytes(value: int) -> bytes:
    return value.to_bytes(8, "little", signed=True) if value < 0 else value.to_bytes(8, "little")


def _read_dstack(uc, x19: int, top: int) -> list[int]:
    out: list[int] = []
    pointer = x19
    while pointer < top:
        chunk = bytes(uc.mem_read(pointer, 8))
        out.append(int.from_bytes(chunk, "little", signed=True))
        pointer += 8
    return list(reversed(out))
