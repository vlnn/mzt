# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**M2 — stack words and arithmetic.** Subroutine-threaded code, 21 primitives:

- Stack: `dup` `drop` `swap` `over` `nip` `rot`
- Arithmetic: `+` `-` `*` `/mod` `negate` `abs`
- Comparison: `=` `<` `>` `0=`
- Bitwise: `and` `or` `xor` `invert`
- I/O: `.` (printf via Apple's stack-only variadic ABI)

Truth values follow Forth convention: `-1` (all bits set) for true, `0` for false.

## Quickstart

```bash
uv sync
make test                    # 248 passing on Linux / 253 on Mac
make examples                # macOS / Apple Silicon only — builds every .fs
./examples/arith             # 21
./examples/square            # 100
./examples/abs               # 7
./examples/add               # 5
./examples/hello             # hello
```

## CLI

```bash
mzt build path/to/source.fs -o path/to/binary
```

Source files must define `: main ... ;` as the entry point.

## Test layers

- **Pure pytest** for tokenizer, compiler, primitive registry, emitter, CLI.
- **clang + Unicorn** for primitive bodies — `clang -arch arm64 -c` produces
  a Mach-O object, a small parser pulls the `__TEXT,__text` bytes out, and
  Unicorn executes them against a synthetic data stack. No keystone, no
  extra installs beyond the clang already needed for the main build.
  ~30 ms per unique primitive (cached for the session) plus ~10 ms per
  test case.
- **End-to-end** via `clang` and the produced Mach-O binary; gated to
  `sys.platform == "darwin"`.

## Roadmap

See `MVP_Plan` for the milestone breakdown (M0 → M6). Next up: M3 control
flow (`if`/`else`/`then`, `begin`/`until`/`while`/`repeat`).
