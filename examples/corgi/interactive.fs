\ Interactive turn loop for corgi adventures.
\
\ Provides run-corgi: intro screen, the play loop, closing message.
\ Reads a line at a time via the `key` primitive (single-byte _read
\ from stdin) — terminal cooked mode delivers the line on ENTER, we
\ keep only the first non-space byte (lowercased) and dispatch on it.
\
\ Mirrors the structure of playthrough.fs: game.fs is the engine,
\ this file is the human driver. Test files include playthrough.fs;
\ this file is what `main` runs.

include game.fs


\ ─── lowercasing ASCII ────────────────────────────────────────────

: ascii-upper?  ( c -- flag )      dup 64 > swap 91 < and ;
: lower         ( c -- c-prime )   dup ascii-upper? if 32 + then ;


\ ─── line input ───────────────────────────────────────────────────
\ Read bytes from stdin until newline (ENTER → byte 10). Keep only
\ the first non-space byte; return it lowercased (or 0 if blank).
\ This sidesteps tokeniser/string-equality work — the dispatcher only
\ ever sees a single byte.

variable input-first

: read-line-first  ( -- c )
    0 input-first !
    begin
        key
        dup 10 = if
            drop  1
        else
            dup 32 = 0=
            input-first @ 0= and
            if input-first ! else drop then
            0
        then
    until
    input-first @ lower ;


\ ─── intro and closing ────────────────────────────────────────────

: intro
    ansi-clear
    ." CORGI ADVENTURES" cr cr
    ." A small dog dropped their ball into the spooky" cr
    ." old well. Be a brave good corgi: bring it home." cr cr
    ." Type and press ENTER. First letter is enough:" cr
    ."   N S E W   move (north, south, east, west)" cr
    ."   T or G    take the thing here" cr
    ."   D         drop something" cr
    ."   L         look around" cr
    ."   I         inventory" cr
    ."   B         bark" cr
    ."   H or ?    help" cr
    ."   Q         quit" cr cr
    ." Press ENTER to start..." cr
    read-line-first drop ;

: closing
    ansi-clear
    show-msg
    cr
    ." Thanks for playing!" cr ;


\ ─── turn loop ────────────────────────────────────────────────────
\ One turn: redraw, read a line, dispatch the first letter. The
\ dispatcher itself sets last-msg / game-over / show-inv? — render
\ on the *next* turn shows the consequence.

: turn
    render
    read-line-first
    dispatch ;

: run-corgi
    intro
    reset-game
    begin
        turn
        won? if celebrate then
        game-over @
    until
    closing ;
