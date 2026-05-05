import sys


def main(argv: list[str] | None = None) -> int:
    sys.stderr.write("mzt: CLI lands in M1 (numbers, +, .). Use mzt.builder.build() for now.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
