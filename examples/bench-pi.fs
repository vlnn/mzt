\ Pi via Leibniz series, fixed-point integer arithmetic.
\
\   pi/4 = 1 - 1/3 + 1/5 - 1/7 + ...
\
\ Scale by 10^7, sum N terms, multiply by 4 at the end. Integer
\ truncation noise dominates the series-convergence error past about
\ N=10^4, so the result is *not* an accurate approximation of pi —
\ but the same source always produces the same output. With
\ N=1,000,000 and scale=10,000,000 the output is 31416020.
\
\ Why this benchmark: dense arithmetic loop body — one /, one *,
\ one +, one branch, two memory ops on the accumulator — no
\ recursion, no string output. Different shape from bench-fib.

include core.fs

variable acc

: pi-term  ( i scale -- )
    over 2 * 1 +
    /
    swap 1 and if negate then
    acc @ + acc ! ;

: pi-loop  ( N scale -- )
    swap 0 do
        i over pi-term
    loop drop ;

: main
    0 acc !
    1000000 10000000 pi-loop
    acc @ 4 * . ;
