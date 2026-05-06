include test-lib.fs

\ sum 1..n via counted loop
: sum-to  ( n -- sum )  0 swap 1+ 1 do i + loop ;

\ factorial via recurse
: fact  ( n -- n! )  dup 1 < if drop 1 else dup 1 - recurse * then ;

: test-sum-1     1 sum-to 1 assert-eq ;
: test-sum-5     5 sum-to 15 assert-eq ;
: test-sum-10    10 sum-to 55 assert-eq ;
: test-fact-0    0 fact 1 assert-eq ;
: test-fact-1    1 fact 1 assert-eq ;
: test-fact-5    5 fact 120 assert-eq ;
: test-fact-7    7 fact 5040 assert-eq ;

: main
    test-sum-1
    test-sum-5
    test-sum-10
    test-fact-0
    test-fact-1
    test-fact-5
    test-fact-7 ;
