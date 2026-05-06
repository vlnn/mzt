"""Smoke test: JIT-compile a function that returns 42, call it from Python.

Apple Silicon only. Requires the host Python binary to be codesigned with
the ``com.apple.security.cs.allow-jit`` entitlement. See README for the
codesign command.
"""
import ctypes
import sys

from mzt.jit.assembler import encode_movz, encode_ret
from mzt.jit.region import JitRegion


def build_returns_42(region: JitRegion) -> int:
    with region.writable():
        addr = region.start_function()
        region.append_u32(encode_movz(0, 42, 0))
        region.append_u32(encode_ret())
    return addr


def main() -> int:
    if sys.platform != "darwin":
        print(f"JIT smoke runs on macOS arm64 only; this is {sys.platform}")
        return 1

    with JitRegion() as region:
        addr = build_returns_42(region)
        func = ctypes.CFUNCTYPE(ctypes.c_uint64)(addr)
        result = func()

    print(f"JIT'd function returned {result}")
    return 0 if result == 42 else 1


if __name__ == "__main__":
    sys.exit(main())
