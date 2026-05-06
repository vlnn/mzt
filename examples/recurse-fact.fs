: fact dup 1 < if drop 1 else dup 1 - recurse * then ;
: main 5 fact . ;
