# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**M1 — numbers, `+`, `.`.** `: main 2 3 + . ;` compiles and prints `5`.
Subroutine-threaded code, data stack pointer pinned in `x19`, 8 KB BSS-backed
data stack, Apple-ABI-correct variadic call into `printf` for `.`.

## Quickstart

```bash
uv sync
make test
make examples            # macOS / Apple Silicon only
./examples/add           # prints 5
./examples/hello         # prints hello
```

## CLI

```bash
mzt build path/to/source.fs -o path/to/binary
```

Source files must define `: main ... ;` as the entry point.

## Roadmap

See `MVP_Plan` for the milestone breakdown (M0 → M6).
