include test-lib.fs

: sum-to  ( n -- sum )  0 swap 1+ 1 do i + loop ;
: fact  ( n -- n! )  dup 1 < if drop 1 else dup 1 - recurse * then ;

: test-sum-1     1 sum-to 1 assert-eq ;
: test-sum-5     5 sum-to 15 assert-eq ;
: test-sum-10    10 sum-to 55 assert-eq ;
: test-fact-0    0 fact 1 assert-eq ;
: test-fact-1    1 fact 1 assert-eq ;
: test-fact-5    5 fact 120 assert-eq ;
: test-fact-7    7 fact 5040 assert-eq ;
