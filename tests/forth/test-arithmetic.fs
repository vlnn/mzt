include test-lib.fs

: test-addition       2 3 + 5 assert-eq ;
: test-subtraction    10 3 - 7 assert-eq ;
: test-multiplication 4 5 * 20 assert-eq ;
: test-division       20 4 / 5 assert-eq ;
: test-modulo         17 5 mod 2 assert-eq ;

: main
    test-addition
    test-subtraction
    test-multiplication
    test-division
    test-modulo ;
