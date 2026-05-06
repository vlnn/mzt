: first-mult  swap 1+ begin swap over over /mod drop 0= 0= while swap 1+ repeat drop ;
: main 10 3 first-mult . ;
