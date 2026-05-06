# mzt

A Forth-like cross-compiler for Apple Silicon (M1/M2/M3/M4). Takes a `.fs`
source file and emits a native ARM64 Mach-O binary by generating text
assembly and shelling out to `clang` for assembly, linking, and ad-hoc
signing in one step. Same pipeline shape as
[`vlnn/zt`](https://github.com/vlnn/zt) (Z80 → ZX Spectrum); the frontend,
IR, and peephole passes are reusable, the back end is rewritten for AArch64.

## Status

**Post-MVP step 8 — vendored stdlib + Forth-side test harness.** Zt's
portable `core.fs` subset is vendored at `src/mzt/stdlib/core.fs`
(`2dup`, `2drop`, `tuck`, `-rot`, `?dup`, `/`, `mod`, `square`, `space`,
`spaces`, `min`, `max`). New `halt ( n -- )` primitive calls libSystem
`_exit(n)`. Forth-side test library at `tests/forth/test-lib.fs`
provides `assert-eq`, `assert-true`, `assert-false`. The Python-side
harness `tests/test_forth.py` walks `tests/forth/test-*.fs`, builds
each binary, runs it, asserts exit code zero. *Adding a new test is
writing one `.fs` file.*

**Previously:** `include` for source-file composition (step 7);
`:noname`/`execute` (step 6); `recurse` and `constant` (steps 4–5);
counted loops (step 3); `1+`/`1-` (step 2); return-stack words
(step 1); variables and memory.

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
./examples/noname-execute         # 12   (inline anonymous thunk + execute)
./examples/noname-runner          # 12 12  (test-runner-style thunks)
./examples/include-helpers        # 10 16   (uses double/square from lib-helpers.fs)
./examples/include-stdlib         # 8 3    (uses 2dup from bundled stdlib core.fs)
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

See `MVP_Plan` for the milestone breakdown (M0 → M6). M0–M5 done
plus all eight post-MVP steps from `next_step`: variables/memory,
return-stack words, `1+`/`1-` plus iteration regression set,
counted loops, `recurse`, `constant`, `:noname`/`execute`, `include`,
and the vendored stdlib + Forth-side test harness.

Beyond `next_step`:
- Promote the Unicorn-based whole-program runner prototype to wired
  test infra. Would unlock running iteration tests on Linux without
  Apple Silicon. Needs a small relocation pass for `WordAddr`-using
  programs.
- Vendor more of zt's stdlib (`array.fs`, `logic.fs`, `bit.fs` —
  the portable subsets).
- Profiler (`mach_absolute_time` deltas), debug-map output,
  primitive inlining, tree-shaking.
- Eventually: REPL with runtime word compilation
  (`MAP_JIT`/`pthread_jit_write_protect_np`/JIT entitlement).
- Eventually: hand-rolled Mach-O + ad-hoc signing (drops the clang
  dependency).
