\ stdlib/core.fs — core Forth words built on mzt's M5 primitives.
\
\ Vendored from zt (vlnn/zt) and adapted for ARM64. Z80-only entries
\ (?dup using :::, struct-accessor sugar via ::, Spectrum cls/screen
\ constants) omitted; ?dup rewritten as a portable colon definition.
\ When zt's upstream changes core.fs, cherry-pick by hand.

\ ─── stack manipulation ────────────────────────────────────────────────
: 2dup    ( a b -- a b a b )    over over ;
: 2drop   ( a b -- )            drop drop ;
: tuck    ( a b -- b a b )      swap over ;
: -rot    ( a b c -- c a b )    rot rot ;

\ Conditional duplicate: leaves a copy of TOS only when TOS is non-zero.
: ?dup    ( n -- 0 | n n )      dup if dup then ;

\ ─── arithmetic ────────────────────────────────────────────────────────
\ /mod is a primitive in mzt. / and mod fall out trivially.
: /       ( a b -- q )          /mod nip ;
: mod     ( a b -- r )          /mod drop ;

: square  ( n -- n*n )          dup * ;

\ ─── output helpers ────────────────────────────────────────────────────
\ cr is a primitive in mzt; space + spaces are colon definitions.
: space   ( -- )                32 emit ;

\ emit n spaces; n<=0 prints nothing
: spaces  ( n -- )
    begin dup 0 > while 1- 32 emit repeat drop ;

\ ─── min/max ────────────────────────────────────────────────────────────
: min     ( a b -- min )        2dup < if drop else nip then ;
: max     ( a b -- max )        2dup > if drop else nip then ;
