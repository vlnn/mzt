: run-test  execute ;
: test-add  :noname 7 5 + ; ;
: test-mul  :noname 4 3 * ; ;
: main test-add run-test . test-mul run-test . ;
