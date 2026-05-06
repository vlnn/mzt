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

## Benchmarks

Two deterministic-output workloads for measuring future optimisation
work (tree-shaking, primitive inlining, peephole rules,
colon-definition inlining):

```bash
make bench                        # builds + times both
./examples/bench-fib              # 9227465  — fib(35), naive recursive
./examples/bench-pi               # 31416020 — Leibniz pi, 10^6 terms, scale 10^7
```

`bench-fib.fs` exercises function-call overhead (~30M `bl`/`ret`
pairs). `bench-pi.fs` exercises loop-body density (one division, one
multiplication, sign flip via `1 and if negate then`, two memory ops
on an accumulator, no recursion). The deterministic values are locked
in by `tests/forth/test_benchmarks.fs` at smaller inputs that run
under a second through pytest.

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
- **Forth-side**: every `tests/**/test_*.fs` file is collected by
  `conftest.py` as a pytest module, and each `: test-foo ;` colon
  definition inside it becomes one pytest item — same workflow as
  Python `test_*.py` files. The test library (`tests/forth/test-lib.fs`)
  provides `assert-eq` / `assert-true` / `assert-false`, which call
  `halt` with non-zero exit on failure. *Adding a new test is dropping
  a `test_*.fs` file in any pytest directory* — pytest discovers it
  next run.

  ```bash
  pytest tests/forth/                                          # all Forth tests
  pytest tests/forth/ -v                                       # see each : test-* word
  pytest -k arithmetic                                         # filter by word name
  pytest tests/forth/test_arithmetic.fs::test-addition         # run a single word
  make forth-test                                              # convenience target
  ```

  Skipped on non-Apple-Silicon machines (clang produces Mach-O arm64
  binaries that only run there).

## JIT backend (work in progress)

A REPL-oriented JIT backend lives at `src/mzt/jit/` alongside the
clang-based AOT path. The plan is in `JIT_Plan`; this is steps 1–4.

**Step 1 — JIT memory region.** `JitRegion` wraps `mmap(MAP_JIT)` plus
`pthread_jit_write_protect_np`, exposes a `with region.writable():`
context that brackets every write, and flushes the icache before
handing control back. Append-only; no relocation table; instruction-
aligned cursor. `tests/test_jit_region.py` covers the pure-logic side
with a fake libc and the platform side with real `mmap` (skipped off
Apple Silicon).

**Step 2 — minimal ARM64 byte assembler.** `src/mzt/jit/assembler.py`
exposes one pure encoder per instruction form the IR emits — `ret`,
`bl`, `blr`, `b`, `b.cond`, `cbz`/`cbnz`, `movz`/`movk`/`movn`,
`add`/`sub` (immediate and register), `adrp`, `str`/`ldr` in three
addressing modes, `stp`/`ldp` pre-indexed and offset, `cmp`, `mov`,
plus a `movz_imm64` helper that lowers an arbitrary 64-bit constant
to a `movz`+`movk` tower with zero chunks skipped. Encodings are
parametrised against `tests/_jit_reference_data.py` (the source of
truth) and a generated audit file `tests/jit_reference_encodings.txt`.

`scripts/verify_jit_encodings.py` rounds the reference set through
`clang -c` and compares per-mnemonic — closes the loop on "verified
against the assembler we ship with". Requires clang.

`scripts/regen_jit_reference.py` regenerates the audit file when
encoders change.

**Step 3 — host library + primitive table.** `src/mzt/jit/host_lib.py`
emits a "primitives-only" assembly file (every non-inline primitive
plus `_print_str`, all `.globl`-exported, plus the `__cstring` and
`__bss` sections those bodies reference) and shells out to
`clang -dynamiclib` to build `build/jit/libmzt_host.dylib`. The dylib
contains the same primitive bytes the AOT path emits — same source,
same body strings — so behaviour is locked together.

`src/mzt/jit/primitive_table.py::PrimitiveTable` is a tiny frozen
name → address map. `load_primitives_from_dylib(path)` opens the
dylib via `ctypes.CDLL`, runs `dlsym` once per primitive label at
build time, and caches the result. From the JIT emitter's point of
view, `table.address("dup")` is a hash lookup that returns an
`int`-shaped absolute address.

**Step 4 — IR-to-bytes emitter.** `src/mzt/jit/emitter.py` takes a
list of IR cells (`Literal`, `PrimRef`, `ColonRef`, `Label`, `Branch`)
and emits a complete callable function: AAPCS64 prologue, body, then
epilogue with `ret`. Each cell type has a small dedicated handler.
`Branch`/`Label` use a two-pass scheme — pass 1 records label
positions and emits placeholder words for branches, pass 2 patches
each placeholder with the resolved relative offset.

Primitive calls go through `movz x16, #addr; blr x16` rather than
`bl <offset>`, because the host dylib and the JIT region can be more
than ±128MB apart on macOS — beyond `bl`'s reach. `movz_imm64` skips
zero chunks so the typical primitive call is 3-4 instructions
instead of 5. `ColonRef` between two JIT'd bodies stays as `bl`
since both live in the same `JitRegion` (max 16KB at MVP).

Inline primitives — currently just `zero` — are inlined byte-for-byte
via the `_INLINE_PRIMITIVE_WORDS` table. `StringLit`, `Addr`, and
`WordAddr` are deferred (they need page-aligned `adrp` against
either the host dylib's `__cstring` / `__bss` or a JIT-controlled
data area).

`tests/test_jit_emitter.py` has 32 byte-level assertions (one per
cell type, branches forward and back, if/else/then composition).
`tests/test_jit_emitter_unicorn.py` has 18 semantic tests that
actually execute the emitted bytes through Unicorn, validating
that primitive calls reach (including a 200TB-distant address that
`bl` could never have hit), branches resolve correctly, and
`ColonRef` between two JIT'd bodies works.

### Smoke tests

```bash
uv run python examples/jit_emitter_smoke.py     # JIT-compiles 2 3 + via Unicorn
uv run pytest scripts/verify_jit_encodings.py   # all 69 encodings match clang
```

The emitter smoke runs anywhere with unicorn installed — no Apple
Silicon, no clang, no JIT entitlement.

### On Apple Silicon

The host Python binary needs the JIT entitlement for Step 1's
`mmap(MAP_JIT)`. Once per dev machine:

```bash
cat > /tmp/jit.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-jit</key><true/>
</dict>
</plist>
PLIST
codesign --entitlements /tmp/jit.plist --force -s - "$(uv run python -c 'import sys; print(sys.executable)')"
```

Then:

```bash
uv run python examples/jit_smoke.py             # JIT'd function returned 42
uv run python examples/jit_host_lib_smoke.py    # builds dylib, resolves all primitives
uv run python examples/jit_emitter_smoke.py     # runs the IR emitter pipeline
```

`jit_host_lib_smoke.py` and `jit_emitter_smoke.py` do not need the
JIT entitlement — they only do dlsym and Unicorn emulation. Only
`jit_smoke.py` exercises real `mmap(MAP_JIT)`.

Without the entitlement, every `mmap(MAP_JIT)` call returns
`MAP_FAILED` and `jit_smoke.py` prints an allocation error.

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
- Eventually: hand-rolled Mach-O + ad-hoc signing (drops the clang
  dependency).
- In progress: REPL with runtime word compilation
  (`MAP_JIT`/`pthread_jit_write_protect_np`/JIT entitlement). Steps
  1–4 of `JIT_Plan` shipped; see "JIT backend" above.
