include test-lib.fs

\ This test deliberately fails. The harness should detect non-zero exit
\ code and report it. We test the negative case via the Python harness's
\ "expected to fail" pattern.

: main 1 2 assert-eq ;
