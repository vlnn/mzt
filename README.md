# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**Post-MVP steps 5+6 — `recurse` and `constant`.** A one-line immediate
that emits a `ColonRef` to the in-progress definition, plus a top-level
`<num> constant <name>` form that registers a one-cell colon definition.
Recursive factorial works (`: fact dup 1 < if drop 1 else dup 1 - recurse * then ;`),
and constants behave as expected (`100 constant max-items`).

**Previously:** counted loops `do`/`loop`/`+loop`/`leave`/`i`/`j` (step 4);
`1+`/`1-` plus iteration-pattern regression set (step 3); return-stack
words `>r`/`r>`/`r@` (step 2); variables and memory (`variable`,
`create`, `allot`, `@`, `!`, `c@`, `c!`).

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
./examples/do-count               # 0 1 2 3 4
./examples/do-sum                 # 15
./examples/do-leave               # 14
./examples/do-nested              # 1 2 2 4 3 6  (3x2 multiplication table)
./examples/recurse-fact           # 120  (5! via recursive factorial)
./examples/constant-area          # 27   (3*3*3, where radius=3 is a constant)
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
variables/memory, return-stack words, `1+`/`1-` plus iteration
regression set, counted loops, `recurse`, and `constant` as the first
six post-MVP steps.

Next per `next_step`: `:noname`/`execute` for first-class quotations
(unlocks zt's test runner pattern), `include` for source file
composition, then vendor zt's `core.fs` and write Forth-side tests.

Possible test infrastructure improvement: a Unicorn-based
whole-program runner that loads the assembled Mach-O and runs colon
words on Linux (no Apple Silicon required), covering iteration
behaviour without `printf`/`write` stubs by using non-IO test
programs that leave results on the data stack. The prototype works;
not yet wired in.
