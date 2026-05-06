import ctypes
from pathlib import Path
from typing import Callable, Iterable

from mzt.ir import Cell
from mzt.jit.emitter import compile_body_to_bytes
from mzt.jit.host_lib import build_host_library, default_host_library_path
from mzt.jit.primitive_table import PrimitiveTable, load_primitives_from_dylib
from mzt.jit.region import JitRegion


_DEFAULT_REGION_SIZE = 1 << 23


TrampolineFn = Callable[[int, int, int], tuple[int, int]]


class JitExecutor:
    def __init__(
        self,
        *,
        primitives: PrimitiveTable,
        region: JitRegion,
        trampoline: TrampolineFn,
        dstack_top: int,
        rstack_top: int,
    ):
        self.primitives = primitives
        self.region = region
        self._trampoline = trampoline
        self.dstack_top = dstack_top
        self.rstack_top = rstack_top
        self.x19 = dstack_top
        self.x20 = rstack_top
        self.word_addresses: dict[str, int] = {}

    @classmethod
    def open(
        cls,
        host_lib_path: Path | None = None,
        *,
        region_size: int = _DEFAULT_REGION_SIZE,
    ) -> "JitExecutor":
        path = Path(host_lib_path) if host_lib_path else default_host_library_path()
        if not path.exists():
            build_host_library(path)
        lib = ctypes.CDLL(str(path))
        primitives = load_primitives_from_dylib(path)
        trampoline = _wrap_trampoline(lib.trampoline)
        dstack_top = _u64_returner(lib.get_dstack_top)()
        rstack_top = _u64_returner(lib.get_rstack_top)()
        region = JitRegion(size=region_size)
        region.__enter__()
        return cls(
            primitives=primitives,
            region=region,
            trampoline=trampoline,
            dstack_top=dstack_top,
            rstack_top=rstack_top,
        )

    def __enter__(self) -> "JitExecutor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.region.close()

    def reset(self) -> None:
        self.x19 = self.dstack_top
        self.x20 = self.rstack_top

    def compile(self, name: str, cells: Iterable[Cell]) -> int:
        cells_list = list(cells)
        body_addr = self.region.here()
        payload = compile_body_to_bytes(
            cells_list,
            base_addr=body_addr,
            primitives=self.primitives,
            word_addresses=self.word_addresses,
        )
        with self.region.writable():
            self.region.append_bytes(payload)
        self.word_addresses[name] = body_addr
        return body_addr

    def execute(self, body_addr: int) -> None:
        self.x19, self.x20 = self._trampoline(self.x19, self.x20, body_addr)

    def execute_word(self, name: str) -> None:
        self.execute(self.word_addresses[name])

    def read_dstack(self) -> list[int]:
        return _read_stack(self.x19, self.dstack_top)

    def read_rstack(self) -> list[int]:
        return _read_stack(self.x20, self.rstack_top)


def _wrap_trampoline(c_trampoline) -> TrampolineFn:
    c_trampoline.argtypes = [
        ctypes.c_uint64,
        ctypes.c_uint64,
        ctypes.c_uint64,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint64),
    ]
    c_trampoline.restype = None

    def call(initial_x19: int, initial_x20: int, body_addr: int) -> tuple[int, int]:
        out_x19 = ctypes.c_uint64()
        out_x20 = ctypes.c_uint64()
        c_trampoline(
            initial_x19,
            initial_x20,
            body_addr,
            ctypes.byref(out_x19),
            ctypes.byref(out_x20),
        )
        return out_x19.value, out_x20.value

    return call


def _u64_returner(c_func) -> Callable[[], int]:
    c_func.argtypes = []
    c_func.restype = ctypes.c_uint64
    return lambda: int(c_func())


def _read_stack(pointer: int, top: int) -> list[int]:
    out: list[int] = []
    cursor = pointer
    while cursor < top:
        chunk = ctypes.string_at(cursor, 8)
        out.append(int.from_bytes(chunk, "little", signed=True))
        cursor += 8
    return list(reversed(out))
