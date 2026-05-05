# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**M4 — output: `emit`, `cr`, `."`.** Byte-level output via `_write` syscalls.
Strings parsed by a character-level tokenizer so spaces inside `." …"` are
preserved verbatim, then interned into a `__cstring` section with each
string getting a unique `Lstr_N` label. Compiled call shape:
`adrp x0, Lstr_N@PAGE ; add x0, x0, Lstr_N@PAGEOFF ; mov x1, #len ; bl _print_str`.

Still in: 23 primitives, control flow, subroutine-threaded code, 8 KB
data stack in `x19`.

## Quickstart

```bash
uv sync
make test                         # 319 passing on Linux / 330 on Apple Silicon
make examples                     # macOS / Apple Silicon only
./examples/hello-text             # Hello, world!
./examples/letter                 # A
./examples/greet                  # Hello, mzt!
./examples/fact                   # 120
./examples/countdown              # 5 4 3 2 1
./examples/ifelse                 # 42
```

## CLI

```bash
mzt build path/to/source.fs -o path/to/binary
```

Source files must define `: main ... ;` as the entry point.

## Test layers

- **Pure pytest** for tokenizer, compiler (including control-flow IR shape),
  primitive registry, emitter, CLI.
- **clang + Unicorn** for primitive bodies (each of the 21 primitives, ~70
  cases) and control-flow semantics (`cbz`/`b` actually jump where the
  emitter says they will). `clang -arch arm64 -c` produces a Mach-O object,
  a small parser pulls the `__TEXT,__text` bytes out, and Unicorn runs
  them against a synthetic data stack. `@lru_cache` amortises the
  per-primitive subprocess cost.
- **End-to-end** via `clang` and the produced Mach-O binary; gated to
  `sys.platform == "darwin"`.

## Roadmap

See `MVP_Plan` for the milestone breakdown (M0 → M6). Next up: M5
peephole framework with the first two rules.
