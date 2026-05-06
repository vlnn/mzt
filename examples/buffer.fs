\ Byte buffer: store ASCII 'H' 'i' '!' then print them via emit.
create buf 4 allot

: main
    72 buf      c!     ( store 'H' at buf[0] )
    105 buf 1 + c!     ( store 'i' at buf[1] )
    33 buf 2 +  c!     ( store '!' at buf[2] )
    buf      c@ emit
    buf 1 +  c@ emit
    buf 2 +  c@ emit
    cr
;
