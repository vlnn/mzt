\ Array of 5 cells filled with 1..5, summed via a counter held in a variable.
create xs 40 allot
variable idx
variable acc

: store-fives
    1 xs       !
    2 xs 8  +  !
    3 xs 16 +  !
    4 xs 24 +  !
    5 xs 32 +  ! ;

: sum-xs
    0 acc !
    0 idx !
    begin
        idx @ 5 <
    while
        xs idx @ 8 * + @
        acc @ + acc !
        idx @ 1 + idx !
    repeat ;

: main
    store-fives
    sum-xs
    acc @ .             ( 1+2+3+4+5 = 15 )
;
