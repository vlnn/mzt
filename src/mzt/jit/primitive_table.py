import ctypes
from pathlib import Path
from typing import Iterable

from mzt.primitives import Primitive, all_primitives


class PrimitiveLookupError(RuntimeError):
    pass


class PrimitiveTable:
    def __init__(self, name_to_address: dict[str, int]):
        for name, addr in name_to_address.items():
            if addr == 0:
                raise PrimitiveLookupError(
                    f"primitive {name!r} resolved to null address"
                )
        self._addrs: dict[str, int] = dict(name_to_address)

    def address(self, name: str) -> int:
        try:
            return self._addrs[name]
        except KeyError:
            raise PrimitiveLookupError(
                f"unknown primitive: {name!r}"
            ) from None

    def has(self, name: str) -> bool:
        return name in self._addrs

    def names(self) -> Iterable[str]:
        return self._addrs.keys()


def load_primitives_from_dylib(path: Path) -> PrimitiveTable:
    lib = ctypes.CDLL(str(path))
    addresses: dict[str, int] = {}
    for primitive in all_primitives():
        if primitive.inline:
            continue
        addresses[primitive.name] = _resolve_or_raise(lib, primitive)
    return PrimitiveTable(addresses)


def _resolve_or_raise(lib, primitive: Primitive) -> int:
    try:
        addr = _resolve_symbol(lib, primitive.label)
    except AttributeError as exc:
        raise PrimitiveLookupError(
            f"symbol {primitive.label!r} not found for primitive {primitive.name!r}: {exc}"
        ) from exc
    if not addr:
        raise PrimitiveLookupError(
            f"symbol {primitive.label!r} for {primitive.name!r} resolved to null/0"
        )
    return addr


def _resolve_symbol(lib, label: str) -> int:
    dlsym_name = label[1:] if label.startswith("_") else label
    func = getattr(lib, dlsym_name)
    return ctypes.cast(func, ctypes.c_void_p).value or 0
