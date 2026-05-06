# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**M5 — peephole framework + two seed rules.** Rules-as-data, sorted by
pattern length so longer patterns always win, applied left-to-right and
iterated to fixpoint so cascading rewrites converge in one optimize call.
Two starter rules:

- `Literal(0)` → `PrimRef("zero")`, inlined as `str xzr, [x19, #-8]!`
  (saves a 4-byte `movz` per occurrence; the `_zero:` function is omitted
  from the runtime since it's never called via bl).
- `swap drop` → `nip` (one `bl _nip` replaces two bl calls).

New rules are appended to a list in `peephole.py`; no other code changes
required.

Still in: 24 primitives, control flow, output (`emit` `cr` `."`), 8 KB
data stack, all of M1–M4.

## Quickstart

```bash
uv sync
make test                         # 348 passing on Linux / 360 on Apple Silicon
make examples
./examples/hello-text             # Hello, world!
./examples/fact                   # 120
./examples/peephole               # 7  (exercises both rules)
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

See `MVP_Plan` for the milestone breakdown (M0 → M6). M0–M5 done.
Next up: M6 — port the portable subset of zt's examples to lock the
language surface in.
