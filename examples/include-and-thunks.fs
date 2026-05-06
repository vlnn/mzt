include lib-helpers.fs

: thunk-double :noname 7 double ; ;
: thunk-square :noname 5 square ; ;
: main thunk-double execute . thunk-square execute . ;
