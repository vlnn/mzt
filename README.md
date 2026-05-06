# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**Post-MVP step 3 — `1+` / `1-` and the iteration regression set.**
Two trivial increment/decrement primitives, three-instruction kernels.
A `regress-iter-*.fs` set covering countdown, accumulator over 1..N (which
also exercises Step-2's `>r`/`r>`), and bounded search — all written
against the existing M3 `begin` loops. They lock the pattern set that
step 4's `do`/`loop` will replace ergonomically, and demonstrate by
construction that counted loops are sugar over what the language already
expresses.

**Previously:** `>r`, `r>`, `r@` (return-stack words on `x20`) and
variables/memory (`variable`, `create`, `allot`, `@`, `!`, `c@`, `c!`).
The compiler tracks return-stack depth per colon body and rejects
unbalanced bodies at `;`.

`allot` is interpret-time and accepts only literal positive integer sizes —
matches standard Forth, keeps the parser obvious, and dodges the harder
runtime-allot question for now.

Still in: M0–M5 (skeleton, primitives, control flow, output, peephole).

## Quickstart

```bash
uv sync
make test
make examples                     # macOS / Apple Silicon only
./examples/counter                # 3
./examples/buffer                 # Hi!
./examples/array-sum              # 15
./examples/hello-text             # Hello, world!
./examples/fact                   # 120
./examples/rstack                 # 50
./examples/rstack-stash           # 56
./examples/regress-iter-countdown # 5 4 3 2 1
./examples/regress-iter-sum       # 15
./examples/regress-iter-search    # 12
```

## CLI

```bash
mzt build path/to/source.fs -o path/to/binary
```

Source files must define `: main ... ;` as the entry point.

## Test layers

- **Pure pytest** for tokenizer, compiler (including control-flow IR shape
  and memory definitions), primitive registry, emitter, CLI.
- **clang + Unicorn** for primitive bodies and control-flow semantics.
  `clang -arch arm64 -c` produces a Mach-O object, a small parser pulls
  the `__TEXT,__text` bytes out, and Unicorn runs them against a
  synthetic data stack. `@lru_cache` amortises the per-primitive
  subprocess cost.
- **End-to-end** via `clang` and the produced Mach-O binary; gated to
  `sys.platform == "darwin"`.

## Roadmap

See `MVP_Plan` for the milestone breakdown (M0 → M6). M0–M5 done plus
variables/memory, return-stack words, and `1+`/`1-` plus the
iteration-pattern regression set as the first three post-MVP steps.

Next per `next_step`: counted loops `do`/`loop`/`+loop`/`leave`/`i`/`j`
(step 4), built on the return-stack discipline already in place. Beyond
that: `recurse`, `constant`, `:noname`/`execute`, `include`, vendor
`core.fs` and write Forth-side tests.
