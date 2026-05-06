\ tests/forth/test_benchmarks.fs — lock in the deterministic outputs of
\ the bench-* examples.
\
\ These are tiny variants of the bench-fib / bench-pi sources with sizes
\ scaled down so the test runs in well under a second. The actual
\ bench-* files in examples/ keep the larger inputs that produce
\ measurable timing differences. Both should always agree on smaller
\ inputs since the algorithms are deterministic.

include core.fs
include test-lib.fs

\ ─── fib ────────────────────────────────────────────────────────────────

: fib  ( n -- result )
    dup 2 < if
    else
        dup 1 - recurse
        swap 2 - recurse
        +
    then ;

: test-fib-base-cases
    0 fib 0 assert-eq
    1 fib 1 assert-eq ;

: test-fib-small
    10 fib 55 assert-eq
    15 fib 610 assert-eq ;

: test-fib-larger
    25 fib 75025 assert-eq ;

\ ─── pi (Leibniz, fixed-point) ─────────────────────────────────────────
\
\ Same algorithm as bench-pi.fs, but uses a small N so the test runs
\ fast. The truncation noise still matches Python ground truth since
\ the math is identical.

variable pi-acc

: pi-term  ( i scale -- )
    over 2 * 1 +
    /
    swap 1 and if negate then
    pi-acc @ + pi-acc ! ;

: pi-loop  ( N scale -- )
    swap 0 do
        i over pi-term
    loop drop ;

: test-pi-tiny
    \ N=100, scale=10000  ->  31320
    0 pi-acc !
    100 10000 pi-loop
    pi-acc @ 4 *  31320 assert-eq ;

: test-pi-small
    \ N=10000, scale=1000000  ->  3141460
    0 pi-acc !
    10000 1000000 pi-loop
    pi-acc @ 4 *  3141460 assert-eq ;
