"""JIT REPL smoke: feed a definition, evaluate an expression, observe the stack.

Apple Silicon only. Requires the JIT entitlement on the Python binary.
This is the programmatic equivalent of `mzt repl --jit`.
"""
import sys

from mzt.jit.repl_executor import JitReplExecutor
from mzt.session import Session


def main() -> int:
    if sys.platform != "darwin":
        print(f"JIT REPL smoke runs on macOS arm64 only; this is {sys.platform}")
        return 1

    repl = JitReplExecutor()
    session = Session()

    try:
        session.feed(": double dup + ;")
        session.feed(": square dup * ;")

        repl(session, "5 double")
        print(f"after '5 double'    : data stack = {repl.data_stack}")

        repl(session, "square")
        print(f"after 'square'      : data stack = {repl.data_stack}")

        repl(session, "1 +")
        print(f"after '1 +'         : data stack = {repl.data_stack}")

        repl.reset()
        print(f"after reset         : data stack = {repl.data_stack}")
    finally:
        repl.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
