import argparse
import sys
from pathlib import Path

from mzt.builder import build_source
from mzt.compiler import CompileError


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "build":
        return _run_build(args.source, args.output)
    parser.error(f"unknown command {args.cmd!r}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mzt")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build", help="compile a .fs source file to a native binary")
    build.add_argument("source", type=Path, help="path to the .fs source file")
    build.add_argument("-o", "--output", type=Path, required=True, help="output binary path")
    return parser


def _run_build(source: Path, output: Path) -> int:
    try:
        build_source(source, output)
    except CompileError as err:
        sys.stderr.write(f"mzt: compile error: {err}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
