\ The turn machinery: command implementations, deferred messages,
\ dispatch from a one-letter key code, and the render cycle.
\
\ Port notes vs zt's app/game.fs:
\ - No tick (' word) and no array literals (w: c:), so cmd-keys[],
\   cmd-actions[], item-printers[], msg-printers[] are all wired at
\   runtime via :noname inside setup-* words. zt does this declaratively
\   at compile time; here it's done at startup.
\ - No read-line / read-key — there is no `key` primitive in mzt yet.
\   `main` runs a scripted command sequence instead, which doubles as
\   a regression demo. Adding interactive input is an open primitive.
\ - cls becomes ANSI 'erase + cursor home' via emit. zt's beep is
\   dropped (Spectrum-only).
\ - No `<>` so use `= 0=`. No `+!` so use `dup @ + swap !` (or 1+ for
\   the increment-by-one case).

include world.fs


variable game-over


\ ─── item names (printers) ────────────────────────────────────────────

: bone-name    ." bone" ;
: stick-name   ." stick" ;
: ball-name    ." red ball" ;

create item-printers  24 allot      \ 3 cells * 8B
: install-item-printer  ( xt id -- )  8 * item-printers + ! ;
: setup-item-printers
    :noname bone-name  ; bone  install-item-printer
    :noname stick-name ; stick install-item-printer
    :noname ball-name  ; ball  install-item-printer ;

: print-item-name   ( id -- )   8 * item-printers + @ execute ;
: announce-here     ( id -- )   ." There is a " print-item-name ." here." cr ;
: print-with-space  ( id -- )   print-item-name space ;


\ ─── inventory and look ──────────────────────────────────────────────

variable any-carried?

: describe-room  here-room @ .description + @ execute ;

: list-items-here
    /items 0 do
        i here? if i announce-here then
    loop ;

: list-inventory
    ." You are carrying: "
    0 any-carried? !
    /items 0 do
        i carrying? if  i print-with-space  1 any-carried? !  then
    loop
    any-carried? @ 0= if ." nothing." then
    cr ;

: look-here   describe-room  list-items-here ;


\ ─── key codes ────────────────────────────────────────────────────────

110 constant key-n
115 constant key-s
101 constant key-e
119 constant key-w
108 constant key-l
116 constant key-t
103 constant key-g
100 constant key-d
105 constant key-i
98  constant key-b
104 constant key-h
63  constant key-?
113 constant key-q


\ ─── deferred messages ────────────────────────────────────────────────

variable last-msg
variable last-item
variable show-inv?

0  constant msg-welcome
1  constant msg-no-exit
2  constant msg-too-scary
3  constant msg-bravely-east
4  constant msg-took
5  constant msg-dropped
6  constant msg-nothing-here
7  constant msg-jaws-empty
8  constant msg-bark
9  constant msg-help
10 constant msg-unknown
11 constant msg-quiet
12 constant msg-celebrate

13 constant /msgs

: print-took       ." You take the "  last-item @ print-item-name ." ." cr ;
: print-dropped    ." You drop the "  last-item @ print-item-name ." ." cr ;
: print-welcome    ." Time for a walk!" cr ;
: print-no-exit    ." You bonk your snoot. No way that direction." cr ;
: print-too-scary  ." TOO SCARY! You whimper and pad back to safety." cr ;
: print-brave      ." Holding the stick high, you brave the well." cr ;
: print-nothing    ." There is nothing here to take." cr ;
: print-empty      ." Your jaws are empty." cr ;
: print-bark       ." WOOF!" cr ;
: print-unknown    ." Awoo? You twirl in confusion." cr ;
: print-quiet      ;

: print-celebrate
    cr
    ." *** GOOD CORGI! ***" cr
    ." You brought the ball home." cr
    ." The puppy upstairs cheers!" cr ;

: print-help
    ." Type a command and press ENTER." cr
    ." First letter is enough:" cr
    ."   N S E W   move (north, south, east, west)" cr
    ."   LOOK      describe surroundings" cr
    ."   TAKE      grab the thing here" cr
    ."   DROP      drop something" cr
    ."   INV       inventory" cr
    ."   BARK      WOOF!" cr
    ."   HELP      this help" cr
    ."   QUIT      stop the game" cr ;

create msg-printers  104 allot     \ 13 cells * 8B
: install-msg  ( xt id -- )  8 * msg-printers + ! ;

: setup-msg-printers
    :noname print-welcome   ; msg-welcome      install-msg
    :noname print-no-exit   ; msg-no-exit      install-msg
    :noname print-too-scary ; msg-too-scary    install-msg
    :noname print-brave     ; msg-bravely-east install-msg
    :noname print-took      ; msg-took         install-msg
    :noname print-dropped   ; msg-dropped      install-msg
    :noname print-nothing   ; msg-nothing-here install-msg
    :noname print-empty     ; msg-jaws-empty   install-msg
    :noname print-bark      ; msg-bark         install-msg
    :noname print-help      ; msg-help         install-msg
    :noname print-unknown   ; msg-unknown      install-msg
    :noname print-quiet     ; msg-quiet        install-msg
    :noname print-celebrate ; msg-celebrate    install-msg ;

: show-msg   last-msg @  8 *  msg-printers + @  execute ;

: maybe-inventory
    show-inv? @ if 0 show-inv? ! list-inventory then ;


\ ─── movement ─────────────────────────────────────────────────────────

: try-go  ( dir -- )
    here-room @ swap exit-of
    dup blocked? if
        drop  msg-no-exit last-msg !
    else
        here-room !  msg-quiet last-msg !
    then ;

: try-east-from-road
    have-stick? if
        well here-room !
        msg-bravely-east last-msg !
    else
        msg-too-scary last-msg !
    then ;

: do-east
    here-room @ road = if
        try-east-from-road
    else
        dir-e try-go
    then ;

: do-north  dir-n try-go ;
: do-south  dir-s try-go ;
: do-west   dir-w try-go ;


\ ─── take and drop ────────────────────────────────────────────────────

: pick-here     ( -- id-or-minus-1 )   here-room @  pick-at ;
: pick-carried  ( -- id-or-minus-1 )   carried      pick-at ;

: do-take
    pick-here
    dup -1 = if
        drop  msg-nothing-here last-msg !
    else
        dup last-item !
        carried swap item-room!
        msg-took last-msg !
    then ;

: do-drop
    pick-carried
    dup -1 = if
        drop  msg-jaws-empty last-msg !
    else
        dup last-item !
        here-room @ swap item-room!
        msg-dropped last-msg !
    then ;


\ ─── other commands ──────────────────────────────────────────────────

: do-bark       msg-bark last-msg ! ;
: do-look       msg-quiet last-msg ! ;
: do-help       msg-help last-msg ! ;
: do-quit       1 game-over ! ;
: do-inventory  1 show-inv? !  msg-quiet last-msg ! ;
: do-empty      msg-quiet last-msg ! ;
: do-unknown    msg-unknown last-msg ! ;


\ ─── dispatcher: parallel byte/cell arrays + lookup ──────────────────

14 constant /commands

create cmd-keys     14 allot          \ 14 bytes
create cmd-actions  112 allot         \ 14 cells * 8B

: install-cmd  ( xt key i -- )
    >r
    r@ cmd-keys + c!
    r> 8 *  cmd-actions + ! ;

: setup-commands
    :noname do-empty     ; 0       0  install-cmd
    :noname do-north     ; key-n   1  install-cmd
    :noname do-south     ; key-s   2  install-cmd
    :noname do-east      ; key-e   3  install-cmd
    :noname do-west      ; key-w   4  install-cmd
    :noname do-look      ; key-l   5  install-cmd
    :noname do-take      ; key-t   6  install-cmd
    :noname do-take      ; key-g   7  install-cmd
    :noname do-drop      ; key-d   8  install-cmd
    :noname do-inventory ; key-i   9  install-cmd
    :noname do-bark      ; key-b  10  install-cmd
    :noname do-help      ; key-h  11  install-cmd
    :noname do-help      ; key-?  12  install-cmd
    :noname do-quit      ; key-q  13  install-cmd ;

variable __cmd-found

: lookup-cmd  ( c -- i-or-minus-1 )
    -1 __cmd-found !
    /commands 0 do
        dup i cmd-keys + c@ = if
            i __cmd-found !  leave
        then
    loop drop
    __cmd-found @ ;

: dispatch  ( c -- )
    lookup-cmd
    dup -1 = if
        drop do-unknown
    else
        8 * cmd-actions + @ execute
    then ;


\ ─── render ──────────────────────────────────────────────────────────
\ ANSI 'erase screen + cursor home'. zt uses cls; mzt does not have
\ display memory or a Spectrum-style screen primitive.

: ansi-clear   27 emit ." [2J"  27 emit ." [H" ;
: prompt       ." > " ;

: render
    ansi-clear
    show-msg
    maybe-inventory
    cr
    look-here
    cr
    prompt ;


\ ─── reset and game lifecycle ─────────────────────────────────────────

: reset-game
    setup-rooms
    setup-item-printers
    setup-msg-printers
    setup-commands
    0 game-over !
    0 show-inv? !
    msg-welcome last-msg !
    kitchen here-room !
    place-items ;

: won?       ball item-room@  kitchen = ;
: celebrate  msg-celebrate last-msg !  1 game-over ! ;
