import ctypes
from contextlib import contextmanager

from mzt.jit import _libc


INSTR_SIZE = 4
PAGE_SIZE = 16384


class JitWriteError(RuntimeError):
    pass


class JitRegionFull(RuntimeError):
    pass


class JitRegion:
    def __init__(self, size: int = PAGE_SIZE, *, libc=None):
        self._libc = libc if libc is not None else _libc.load_system_libc()
        self._size = _round_up_page(size)
        self._base = self._libc.allocate_jit(self._size)
        self._cursor = 0
        self._writable = False

    @property
    def base(self) -> int:
        return self._base

    @property
    def size(self) -> int:
        return self._size

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def remaining(self) -> int:
        return self._size - self._cursor

    def here(self) -> int:
        return self._base + self._cursor

    def start_function(self) -> int:
        return self.here()

    @contextmanager
    def writable(self):
        self._enter_writable()
        try:
            yield self
        finally:
            self._exit_writable()

    def _enter_writable(self) -> None:
        self._libc.set_writable(True)
        self._writable = True

    def _exit_writable(self) -> None:
        self._writable = False
        self._libc.set_writable(False)
        self._libc.flush_icache(self._base, self._size)

    def append_u32(self, instruction: int) -> int:
        self._require_writable()
        self._require_capacity(INSTR_SIZE)
        target = self.here()
        _write_u32(target, instruction)
        self._cursor += INSTR_SIZE
        return target

    def append_u32_many(self, instructions) -> int:
        first = self.here()
        for word in instructions:
            self.append_u32(word)
        return first

    def patch_u32(self, address: int, instruction: int) -> None:
        self._require_writable()
        self._require_in_region(address, INSTR_SIZE)
        _write_u32(address, instruction)

    def read_u32(self, address: int) -> int:
        self._require_in_region(address, INSTR_SIZE)
        return _read_u32(address)

    def close(self) -> None:
        if self._base:
            self._libc.deallocate(self._base, self._size)
            self._base = 0
            self._cursor = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _require_writable(self) -> None:
        if not self._writable:
            raise JitWriteError(
                "writes to a JitRegion are only allowed inside a writable() block"
            )

    def _require_capacity(self, n: int) -> None:
        if self.remaining < n:
            raise JitRegionFull(
                f"need {n} bytes, only {self.remaining} bytes remain in {self._size}-byte region"
            )

    def _require_in_region(self, address: int, n: int) -> None:
        end = self._base + self._size
        if address < self._base or address + n > end:
            raise ValueError(
                f"address 0x{address:x}+{n} outside region [0x{self._base:x}, 0x{end:x})"
            )


def _round_up_page(size: int) -> int:
    return (size + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)


def _write_u32(address: int, instruction: int) -> None:
    word = instruction & 0xFFFFFFFF
    ctypes.memmove(address, word.to_bytes(4, "little"), INSTR_SIZE)


def _read_u32(address: int) -> int:
    raw = (ctypes.c_ubyte * INSTR_SIZE).from_address(address)
    return int.from_bytes(bytes(raw), "little")
