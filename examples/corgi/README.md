# Corgi (mzt port)

A port of zt's [`examples/corgi`](https://github.com/vlnn/zt/tree/main/examples/corgi)
text adventure to mzt. A small dog dropped their red ball into the
spooky old well; you, the goodest corgi, must fetch it home.

The port is **interactive** — type a letter (or word), press ENTER, your
corgi acts. The terminal's cooked mode does the buffering for free; mzt
just needs a single-byte `key` primitive (libSystem `_read` from fd 0).

A scripted-winning playthrough (`play` in `playthrough.fs`) still exists
for the test suite — `: test-scripted-playthrough-wins` exercises the
whole world model end-to-end without keyboard input.

## What this exists for

The previous turn's prioritisation document had "custom stacks for
structures" as item 5 with three plausible interpretations. This port
is the friction-finding exercise — sitting down to write it surfaced
the actual gaps between mzt and "what a Forth program of this shape
needs." The friction inventory below is the deliverable; the running
adventure is the evidence.

## Build and play

```bash
uv run mzt build examples/corgi/main.fs -o examples/corgi/main
./examples/corgi/main
```

Or with the convenience target:

```bash
make corgi
```

You'll get an intro screen and then your corgi is in the kitchen.
Type and press ENTER:

| Verb | Action |
|---|---|
| `n` `s` `e` `w` | move (north, south, east, west) |
| `t` or `g` | take the thing here |
| `d` | drop something |
| `l` | look around |
| `i` | inventory |
| `b` | bark |
| `h` or `?` | help |
| `q` | quit |

To win: pick up the stick from the garden, head north then east to
brave the well, take the ball, bring it home to the kitchen, drop it.

## Test

```bash
pytest tests/test_corgi_example.py             # Python-side, runs anywhere
pytest examples/corgi/tests/test_corgi.fs      # Forth-side, Apple Silicon
```

## World

```
   well
    |
   road
    |
  garden    ← stick lives here
    |
  hallway
    |
  kitchen   ← start. Bone here. Drop the ball here to win.
```

The stick gates the road→well corridor: empty-pawed you whimper back.

## Source layout

```
corgi/
├── README.md         this file
├── main.fs           entry point: `: main run-corgi ;` and nothing else
├── interactive.fs    intro, input loop, run-corgi (uses `key`)
├── playthrough.fs    walk-to-stick, fetch-ball, bring-it-home, play
├── world.fs          rooms, items, exits, queries
├── game.fs           commands, dispatch, render, deferred messages
└── tests/
    └── test_corgi.fs   Forth-side assertion tests, ported from zt
```

`game.fs` is the engine; everything else drives it. `interactive.fs`
is the human driver; `playthrough.fs` is the test driver. `main.fs`
chooses interactive (it includes `interactive.fs`); test files
choose scripted (they include `playthrough.fs`).

The split between `main.fs` and `playthrough.fs` exists for the test
harness — see "Forth-test harness `: main` strip" in the friction
inventory below.

---

## Friction inventory

Every zt feature corgi uses, mapped to its mzt fate. **Severity** is
how much it cost the port: *cosmetic* (rewrite a line), *structural*
(rewrite a section), *blocking* (the feature is missing entirely).

### Standard Forth missing from mzt

| Feature | What it does | mzt workaround | Severity |
|---|---|---|---|
| `'` (tick) | Compile-time word → xt | `:noname WORD ;` runtime trampoline + variable cell | **structural** |
| `[']` | Immediate tick | same as above | structural |
| `,` (comma) | Inline a cell into the dictionary at compile time | `create x N allot` + runtime `!` to fill | structural |
| `c,` | Same for byte | runtime `c!` to fill | structural |
| `exit` | Early return from a colon | nest if/else, or use `leave` for loops, or sentinel cell | cosmetic |
| `+!` | Add value to cell | `dup @ rot + swap !` | cosmetic |
| `<>` | Not-equal | `= 0=` | cosmetic |
| `u.` | Unsigned print | `.` (fine for non-negative) | cosmetic |
| `fill` | Fill memory range with byte | `do` loop + `c!` | cosmetic |
| `key` | Read one byte from stdin (blocking) | **shipped as a primitive in this round.** Single libSystem `_read(0, &byte, 1)`, returns -1 on EOF/error. ~13 instructions. The cooked-mode terminal does line buffering for free, so this one primitive is enough for line-at-a-time games — `key?` and `accept` are still missing but didn't end up being needed for corgi. |
| `key?` | Non-blocking byte poll | not implemented; would require `select()` or terminal mode change |
| `accept` | Read a line | not implemented; corgi rolls its own `read-line-first` over `key` |
| `s=`, `compare` | String equality | none (would be needed for word-typed input — corgi sidesteps with first-letter dispatch) |

### zt-specific extensions

| Feature | What it does | mzt workaround | Severity |
|---|---|---|---|
| `STRUCT` | Typed struct definitions with named fields | manual offset constants (`0 constant .exits`, `32 constant .description`) | structural |
| `w:` / `c:` | Cell/byte array literals | `create x N allot` + runtime fills via `:noname … ; addr !` | structural |
| `a-word@/!`, `a-byte@/!` | Indexed array access | `idx 8 *  array +  @` (or `c@` for bytes) | cosmetic |
| `a-count` | Length of an array literal | track separately as a `constant` | cosmetic |
| `for-each-word`, `index-of?-word`, `map-word`, `count-if-word` | Array HOFs taking xts | hand-rolled `do` loop, sometimes with sentinel cell | structural |
| `>@` | Fetch through xt | `@ execute` | cosmetic |
| `require` | zt's include | `include` (rename) | cosmetic |
| `cls` | Spectrum screen clear | ANSI `\x1b[2J\x1b[H` via `emit` | cosmetic |
| `beep` | Spectrum sound | drop, or `7 emit` (BEL) | cosmetic |

### mzt parser quirks worth flagging

| Where | What happens |
|---|---|
| `allot` parser | Only accepts a literal positive integer, not `/room` or `/items /cell *`. Forced repetition of `40 allot`, `24 allot`, `112 allot`. |
| `(` paren comments | Single-pass scan for the first `)`; `( n -- fib(n) )` ends the comment at the wrong `)`. Works around with paren-free identifier names in stack effects. |
| `:noname` | Only valid inside a colon definition body. Pushes the xt at *runtime*, not compile time. So `:noname … ; constant foo` doesn't compile (`constant` reads a literal token, not the data stack). All dispatch tables must be wired by a `setup-*` colon definition that runs once at startup. |
| `'` in source | Not a primitive at all; first attempt hits a generic "unknown word" error. |
| `Makefile` example rule | `examples/%: examples/%.fs` doesn't follow into subdirectories. Subdirectory examples must be built directly via `uv run mzt build`. |
| Forth-test harness `: main` strip | `forth_test_runner.synthesize_test_main` strips `: main` from the test file's *own* source via regex, then appends `: main test-foo ;`. The strip doesn't follow `include`s, so any included file that itself defines `: main` collides at compile time. The port works around this by splitting the entry point off into `main.fs` (just `: main`) and the rest into `playthrough.fs` (everything else). Test files include `playthrough.fs`, never `main.fs`. |

### What hurt the most

In rough order of how much this port wished mzt had it:

1. **`'` (tick)**. Five rooms, three items, thirteen messages, fourteen
   commands — every one of them wants a compile-time xt. The
   `:noname WORD ; addr !` trampoline pattern works but balloons every
   table-of-functions into a `setup-*` word that has to run before the
   table is usable. zt's `w: msg-printers ' print-welcome ' print-no-exit ... ;`
   is one line of intent; mzt's equivalent is fourteen lines of
   `:noname … ; install-msg`, plus an extra `setup-msg-printers` call
   in `reset-game`, plus an extra `install-msg` helper. About a third
   of `game.fs` is mechanical bookkeeping that wouldn't exist with
   tick.

2. **`,` (comma)**. Same shape as `'`: zt's
   `create kitchen -1 , -1 , -1 , -1 , ' kitchen-desc ,` fits on one
   line; mzt's equivalent is `create kitchen 40 allot` plus runtime
   stores in `clear-exits` and `setup-rooms`. The runtime initialisation
   is conceptually identical to `init-exits` (which zt also runs at
   startup), so the gap here is smaller than it looks — but it's still
   compile-time data structure declaration becoming runtime code.

3. **`STRUCT`**. Less acute because the substitution is mechanical
   (`8 constant /cell  40 constant /room  0 constant .exits  32 constant .description`)
   and the substitution preserves zt's intent. The pain is in
   `allot`-not-accepting-a-constant: every record allocation has to
   re-spell the literal `40` rather than `/room`.

4. **`exit`**. Three or four sites in the port wanted it (`pick-at`,
   movement guards, dispatch fallbacks). Workarounds are local — nest
   if/else, or use `leave` inside `do` loops with a sentinel
   variable — but each one is a small structural rewrite of code
   whose intent was "give up early, the answer is right here."

5. **No `key`/`accept`**. Hard stop for interactivity. Adding `key`
   alone (single-byte blocking read) is one libSystem `_read` call —
   maybe three lines in `primitives.py`. `accept` and line buffering
   layer on top. `key?` (non-blocking) needs `select()` or terminal
   mode tweaking and is genuinely harder.

### What didn't hurt at all

- **`include`** matched zt's `require` semantically; one `s/require/include/`
  pass and the multi-file structure worked.
- **`:noname` + `execute`** is enough for first-class function
  pointers. Verbose without `'` but powerful.
- **`do`/`loop` + `leave`** covered every iteration corgi needed.
  `leave` filled in for `exit` inside loops cleanly.
- **`recurse`** wasn't needed by corgi but was present.
- **`create` + `allot`** plus `!`/`@`/`c!`/`c@` covers every memory
  pattern in the original. The runtime-init shape is more verbose
  but not harder to think about.

---

## What this implies for prioritisation

Going back to the post-step-8 priority list:

- **The `'` (tick) gap is the single highest-leverage missing word
  for "real Forth programs."** Adding it is implementation-shaped:
  it's a compile-time intrinsic that emits a `WordAddr` at the
  current point, identical in shape to what `:noname` does for
  anonymous bodies. Probably 30 lines in `compiler.py` plus
  parametrised tests. **Promote this to its own slot, ahead of
  custom stacks.** It's a one-evening change that removes the
  single biggest source of boilerplate in any data-driven Forth
  program.

- **Custom stacks**: the IF-game shape didn't actually want them.
  Corgi gets by with one mutable variable per "stack of N things"
  — `item-loc[3]`, `cmd-keys[14]`, `cmd-actions[14]`,
  `msg-printers[13]`. None of these are stack-shaped at use time;
  they're random-access tables indexed by id or by linear search.
  So **interpretation A (typed companion stacks pinned in `xN`)
  is solving a problem the example doesn't have**. Interpretation B
  (heap-allocated growable arrays) might come up in a different
  example — sprite lists for an arcade game, where things are added
  and removed at runtime — but corgi's data is statically sized.
  This bumps custom stacks back down the priority list.

- **`,` and `c,`** are the natural follow-on to `'`. Same shape:
  inline a cell at the current dictionary point. Probably another
  30 lines and unlocks compile-time array literals (`create xs 1 ,
  2 , 3 , 4 ,`). With `'` and `,` together, zt's `w:`/`c:` array
  literals become two-line user-space colon definitions and the
  port stops needing setup-* words.

- **`exit`**. Less critical than `'` and `,` but pops up everywhere.
  Compile-time, emits `ldp x29, x30, [sp], #16; ret`. Nest-aware so
  it works inside loops. Maybe an evening with the edge cases
  around `do` loops and return-stack frames. Mid-priority.

- **`+!`, `<>`, `u.`, `fill`** are all stdlib-grade colon definitions
  that could ship as part of `core.fs`. None require new primitives.
  An afternoon to add and test.

- **`key`** is its own decision. Adding it is small (3-line
  primitive), but it's the minimum step toward an actually
  interactive corgi. Worth doing the day someone wants an
  interactive example. Doesn't compose with anything else on the
  optimisation roadmap.

The revised top of the priority list is:

1. Tree-shaking *(unchanged from the previous doc)*
2. **`'` (tick)** *(new, promoted from this exercise)*
3. **`,` and `c,`** *(new, follow-on)*
4. Primitive inline flag tweak
5. More peephole rules
6. **`exit`** *(new, mid-priority)*
7. Colon-definition inlining
8. Custom stacks *(demoted; corgi shows it isn't the bottleneck)*
9. REPL

Items 2, 3, 6 weren't visible from the optimisation-only frame of
the previous doc. The IF-game exercise was meant to surface exactly
this kind of language-level gap, and it did.
