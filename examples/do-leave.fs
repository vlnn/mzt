: first-mult-of  100 10 do i over /mod drop 0= if drop i leave then loop ;
: main 7 first-mult-of . ;
