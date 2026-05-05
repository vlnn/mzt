# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**M0 — toolchain skeleton.** Hand-written `examples/hello.s` builds and runs
through the `mzt.builder.build` entry point. No Forth yet.

## Quickstart

```bash
uv sync
make test
make examples   # macOS / Apple Silicon only
./examples/hello
```

## Roadmap

See `MVP_Plan` for the milestone breakdown (M0 → M6).
