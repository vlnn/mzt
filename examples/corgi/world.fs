\ The static world: items, directions, rooms, the corridors between them,
\ and where things start out. Run-time mutable state — the player's
\ location and where each item is — lives here too, since every query
\ touches it.
\
\ Port notes vs zt:
\ - No STRUCT, so /room layout is hand-crafted offset constants.
\ - No , or ' at compile time, so room records are 'create + allot' and
\   description-xt slots are wired at runtime by setup-rooms via :noname.
\ - No w:/c: array literals, so the edge table is filled in install-edges
\   one row at a time. Adding a corridor is one block, not one row.
\ - No exit (early colon return), so pick-at uses 'leave + sentinel cell'.

include core.fs


\ ─── room layout (8-byte cells; mzt is 64-bit) ─────────────────────────
\ /room is 4 exits * 8B + 1 description xt * 8B = 40B.

8  constant /cell
40 constant /room
0  constant .exits          \ offset of first exit cell
32 constant .description    \ offset of description xt slot


\ ─── items, sentinels, directions ──────────────────────────────────────

0 constant bone
1 constant stick
2 constant ball
3 constant /items

-1 constant nowhere
-2 constant carried

0 constant dir-n
1 constant dir-s
2 constant dir-e
3 constant dir-w

: opposite-dir  ( dir -- dir-prime )  1 xor ;


\ ─── room descriptions ────────────────────────────────────────────────
\ One word per room. setup-rooms wraps each in :noname and stores the
\ resulting xt into the room's .description slot at runtime.

: kitchen-desc
    ." You are in your warm kitchen." cr
    ." Your bowl smells faintly of dinner." cr
    ." A bright hallway lies to the NORTH." cr ;

: hallway-desc
    ." A sunny hallway." cr
    ." The kitchen is to the SOUTH." cr
    ." The front door stands open NORTH to the garden." cr ;

: garden-desc
    ." Wonderful, wonderful grass!" cr
    ." The hallway is back SOUTH." cr
    ." A gap in the fence leads NORTH to the road." cr ;

: road-desc
    ." A quiet country road." cr
    ." The garden is back SOUTH." cr
    ." An old WELL stands EAST in a misty field." cr ;

: well-desc
    ." A deep, dark, scary well." cr
    ." You can hear faint whimpering far below." cr
    ." The road is back to the WEST." cr ;


\ ─── room records ─────────────────────────────────────────────────────
\ Uninitialized memory; setup-rooms fills in exits and description xt.

create kitchen   40 allot
create hallway   40 allot
create garden    40 allot
create road      40 allot
create well      40 allot


\ ─── exit cell access ─────────────────────────────────────────────────

: exit-cell  ( room dir -- addr )  /cell *  swap .exits +  + ;
: exit-of    ( room dir -- target )  exit-cell @ ;
: blocked?   ( target -- flag )  -1 = ;
: connect    ( target room dir -- )  exit-cell ! ;

: connect-pair  ( a b dir -- )
    >r  2dup swap  r@           connect
    r>           opposite-dir   connect ;


\ ─── clearing a room's exits ─────────────────────────────────────────
\ All four cells go to -1. mzt has no fill, so unrolled stores it is.

: clear-exits  ( room -- )
    -1 over .exits          + !
    -1 over .exits  8 +     + !
    -1 over .exits 16 +     + !
    -1 over .exits 24 +     + !
    drop ;

: install-desc  ( xt room -- )  .description + ! ;


\ ─── exit table ──────────────────────────────────────────────────────
\ Four bidirectional corridors. With no w:/c: literals we install them
\ explicitly. Order: kitchen-hallway-garden-road-well, all north except
\ the last (east).

: install-edges
    kitchen hallway  dir-n  connect-pair
    hallway garden   dir-n  connect-pair
    garden  road     dir-n  connect-pair
    road    well     dir-e  connect-pair ;


\ ─── reset-rooms ─────────────────────────────────────────────────────
\ Wipe every exit, then install corridors and description xts. The
\ :noname-stored xts are the closest mzt analogue to ' kitchen-desc:
\ they materialise at runtime, not at dictionary-write time.

: reset-room-exits
    kitchen clear-exits
    hallway clear-exits
    garden  clear-exits
    road    clear-exits
    well    clear-exits ;

: setup-rooms
    reset-room-exits
    install-edges
    :noname kitchen-desc ; kitchen install-desc
    :noname hallway-desc ; hallway install-desc
    :noname garden-desc  ; garden  install-desc
    :noname road-desc    ; road    install-desc
    :noname well-desc    ; well    install-desc ;

: init-exits  setup-rooms ;


\ ─── player and item state ─────────────────────────────────────────────

variable here-room

create item-loc    24 allot
create item-homes  24 allot

: item-room@   ( id -- where )  /cell * item-loc + @ ;
: item-room!   ( where id -- )  /cell * item-loc + ! ;

: setup-item-homes
    kitchen  0 /cell * item-homes + !
    garden   1 /cell * item-homes + !
    well     2 /cell * item-homes + ! ;

: place-items
    setup-item-homes
    /items 0 do
        i /cell * item-homes + @  i item-room!
    loop ;


\ ─── item queries ──────────────────────────────────────────────────────

: in-room?     ( id room -- flag )  swap item-room@ = ;
: room-has?    ( id room -- flag )  in-room? ;
: carrying?    ( id -- flag )       item-room@ carried = ;
: have-stick?  ( -- flag )          stick carrying? ;
: here?        ( id -- flag )       item-room@ here-room @ = ;


\ ─── item search ──────────────────────────────────────────────────────
\ pick-at finds the first item id whose location matches `where`, or -1.
\ zt uses index-of?-word + exit; mzt has no exit, so we use a sentinel
\ cell plus leave inside the do loop.

variable __pick-result

: pick-at  ( where -- id-or-minus-1 )
    -1 __pick-result !
    /items 0 do
        dup i item-room@ = if
            i __pick-result !
            leave
        then
    loop drop
    __pick-result @ ;
