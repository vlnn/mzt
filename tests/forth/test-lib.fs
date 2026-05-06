\ tests/forth/test-lib.fs — assertion words for Forth-side tests.
\
\ Convention: a test program runs to completion with exit code 0 if all
\ assertions pass, or non-zero (via halt) on the first failure. The
\ Python harness (tests/test_forth.py) walks tests/forth/test-*.fs,
\ builds each, runs each, and asserts exit code zero.
\
\ Failures print a brief diagnostic to stdout before halting so the
\ harness can capture and surface the message.

include core.fs

\ assert top two stack cells are equal (consumes both).
: assert-eq  ( actual expected -- )
    2dup = if 2drop else
        \ FAIL <expected> <actual>\n
        70 emit 65 emit 73 emit 76 emit 32 emit
        swap . . cr
        1 halt
    then ;

\ assert flag is non-zero (truthy).
: assert-true  ( flag -- )
    if else
        70 emit 65 emit 73 emit 76 emit 32 emit
        84 emit 82 emit 85 emit 69 emit cr
        1 halt
    then ;

\ assert flag is zero (falsy).
: assert-false  ( flag -- )
    if
        70 emit 65 emit 73 emit 76 emit 32 emit
        70 emit 65 emit 76 emit 83 emit 69 emit cr
        1 halt
    then ;
