import argparse
import sys
from pathlib import Path

from mzt.builder import build_source
from mzt.compiler import CompileError
from mzt.repl import Repl
from mzt.repl_driver import run_interactive
from mzt.repl_executor import ClangExecutor


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "build":
        return _run_build(args.source, args.output)
    if args.cmd == "repl":
        return _run_repl(args.include_dirs, jit=args.jit)
    parser.error(f"unknown command {args.cmd!r}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mzt")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build", help="compile a .fs source file to a native binary")
    build.add_argument("source", type=Path, help="path to the .fs source file")
    build.add_argument("-o", "--output", type=Path, required=True, help="output binary path")
    repl = sub.add_parser("repl", help="start an interactive REPL session")
    repl.add_argument(
        "-I", "--include-dir",
        dest="include_dirs",
        action="append",
        type=Path,
        default=[],
        help="extra directory to search for include files",
    )
    repl.add_argument(
        "--jit",
        action="store_true",
        help="use the JIT executor (Apple Silicon only; needs JIT entitlement)",
    )
    return parser


def _run_build(source: Path, output: Path) -> int:
    try:
        build_source(source, output)
    except CompileError as err:
        sys.stderr.write(f"mzt: compile error: {err}\n")
        return 1
    return 0


def _run_repl(include_dirs: list[Path], *, jit: bool = False) -> int:
    executor = _make_jit_executor() if jit else ClangExecutor()
    repl = Repl(executor=executor, include_dirs=include_dirs)
    try:
        run_interactive(repl, stdin=sys.stdin, stdout=sys.stdout)
    finally:
        close = getattr(executor, "close", None)
        if close is not None:
            close()
    return 0


def _make_jit_executor():
    from mzt.jit.repl_executor import JitReplExecutor
    return JitReplExecutor()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
