\ Variables: a simple counter incremented three times.
variable counter

: bump   counter @ 1 + counter ! ;

: main
    0 counter !
    bump bump bump
    counter @ .
;
