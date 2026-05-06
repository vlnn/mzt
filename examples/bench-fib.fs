\ Naive recursive Fibonacci. Benchmark for function-call overhead.
\
\   fib n = n                  when n < 2
\   fib n = fib n-1 + fib n-2  otherwise
\
\ fib 35 = 9227465. Each call does constant work; ~30 million calls
\ in total. This is the workload primitive- and colon-inlining most
\ affect: shrink the per-call body and the saving multiplies by call
\ count.

: fib  ( n -- result )
    dup 2 < if
    else
        dup 1 - recurse
        swap 2 - recurse
        +
    then ;

: main
    35 fib . ;
