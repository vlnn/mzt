\ Array of 5 cells filled with 1..5, summed via a counter held in a variable.
create xs 40 allot
variable i
variable acc

: store-fives
    1 xs       !
    2 xs 8  +  !
    3 xs 16 +  !
    4 xs 24 +  !
    5 xs 32 +  ! ;

: sum-xs
    0 acc !
    0 i !
    begin
        i @ 5 <
    while
        xs i @ 8 * + @
        acc @ + acc !
        i @ 1 + i !
    repeat ;

: main
    store-fives
    sum-xs
    acc @ .             ( 1+2+3+4+5 = 15 )
;
