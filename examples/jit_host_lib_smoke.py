"""Smoke test: build the JIT host dylib and resolve every primitive via dlsym.

Apple Silicon only. Unlike examples/jit_smoke.py this does NOT need the
JIT entitlement; it only loads a dylib and reads exported symbol
addresses.
"""
import sys

from mzt.jit.host_lib import build_host_library, default_host_library_path
from mzt.jit.primitive_table import load_primitives_from_dylib


def main() -> int:
    if sys.platform != "darwin":
        print(f"host-lib smoke runs on macOS arm64 only; this is {sys.platform}")
        return 1

    out = default_host_library_path()
    print(f"building {out}...")
    build_host_library(out)

    print(f"loading {out} via ctypes.CDLL...")
    table = load_primitives_from_dylib(out)

    names = sorted(table.names())
    print(f"resolved {len(names)} primitives:")
    for name in names:
        print(f"  {name:>14s} -> {table.address(name):#018x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
