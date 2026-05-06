include test-lib.fs

: test-2dup
    1 2 2dup
    \ stack ( 1 2 1 2 ); pop and verify each, top first
    2 assert-eq
    1 assert-eq
    2 assert-eq
    1 assert-eq ;
: test-tuck        7 9 tuck 9 assert-eq 7 assert-eq 9 assert-eq ;
: test-rot         1 2 3 rot 1 assert-eq 3 assert-eq 2 assert-eq ;
: test-min-pos     7 3 min 3 assert-eq ;
: test-min-neg     -5 -2 min -5 assert-eq ;
: test-max-pos     7 3 max 7 assert-eq ;
: test-square      6 square 36 assert-eq ;
: test-?dup-zero   0 ?dup 0 assert-eq ;
: test-?dup-five   5 ?dup 5 assert-eq 5 assert-eq ;
