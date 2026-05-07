"""Step 7 smoke: schedule a Forth function on the libdispatch main queue.

Apple Silicon only. Note: a scheduled block actually fires only when
something pumps the main queue. This smoke verifies the dispatch
primitive resolves, compiles, and the call returns without crashing —
the block sits queued until a runloop drains it (Step 8 brings the
:graphics meta-command which runs the runloop).

To prove the block fires, you can paste this into Python and call
CFRunLoopRunInMode after dispatch:

    from ctypes import CDLL, c_double, c_bool
    cf = CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cf.CFRunLoopGetMain.restype = ctypes.c_void_p
    cf.CFRunLoopRunInMode.argtypes = [ctypes.c_void_p, c_double, c_bool]
    cf.CFRunLoopRunInMode(cf.CFRunLoopGetMain(), 0.05, True)
"""
import sys

from mzt.jit.repl_executor import JitReplExecutor
from mzt.session import Session


def main() -> int:
    if sys.platform != "darwin":
        print(f"dispatch-main smoke runs on macOS arm64 only; this is {sys.platform}")
        return 1

    repl = JitReplExecutor()
    session = Session()

    try:
        session.feed(": draw-once 42 ;")
        session.feed(": schedule-draw  :noname draw-once ; dispatch-main ;")

        repl(session, "schedule-draw")
        print("schedule-draw returned without crashing — the block is now queued on main")
        print(f"data stack after dispatch  : {repl.data_stack}")
        print("(the block will fire when something pumps the main runloop)")
    finally:
        repl.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
