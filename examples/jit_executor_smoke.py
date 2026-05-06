"""Step 5 smoke: build the host dylib, JIT-compile '2 3 +', execute it for real.

Apple Silicon only. Requires the Python binary to be codesigned with
the JIT entitlement (see README for the codesign command).
"""
import sys

from mzt.ir import ColonRef, Literal, PrimRef
from mzt.jit.executor import JitExecutor


def main() -> int:
    if sys.platform != "darwin":
        print(f"JIT executor smoke runs on macOS arm64 only; this is {sys.platform}")
        return 1

    with JitExecutor.open() as executor:
        executor.compile("two-plus-three", [Literal(2), Literal(3), PrimRef("+")])
        executor.execute_word("two-plus-three")
        print(f"after 2 3 + : data stack = {executor.read_dstack()}")

        executor.reset()
        executor.compile("forty-two", [Literal(40), Literal(2), PrimRef("+")])
        executor.compile("call-it", [ColonRef("forty-two")])
        executor.execute_word("call-it")
        print(f"after call-it (40 2 + via colon ref): data stack = {executor.read_dstack()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
