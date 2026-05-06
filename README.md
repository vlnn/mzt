# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**Post-MVP step 2 — return-stack words.** `>r`, `r>`, `r@` move cells
between the data stack (`x19`) and a second pinned, callee-saved stack
in `x20`. The runtime reserves `Lrstack_base` (4 KB) in `.bss` and
`_main` initialises `x20` to its top. The compiler tracks return-stack
depth per colon body: `>r` increments, `r>`/`r@` underflow if depth is
zero, and `;` rejects unbalanced bodies with a message naming the
definition. `r_depth` resets between definitions.

**Previously:** variables and memory (`variable`, `create`, `allot`,
`@`, `!`, `c@`, `c!`) compile against a single `Luser_mem` `.zerofill`
block sized per-program; addresses resolve via `adrp/add` to the
block's base plus a bump-pointer offset.

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
variables/memory and return-stack words as the first two post-MVP steps.

Next per `next_step`: `1+`/`1-` plus iteration regression examples
(step 2), then counted loops `do`/`loop`/`+loop`/`leave`/`i`/`j`
(step 3). Beyond that: `recurse`, `constant`, `:noname`/`execute`,
`include`, vendor `core.fs` and write Forth-side tests.
