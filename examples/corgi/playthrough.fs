\ Scripted winning playthrough as importable colon definitions.
\
\ This file deliberately does NOT define `: main`. Test files include
\ this directly (not main.fs), because the Forth-test harness strips
\ `: main` only from the test file's own source — not from anything
\ it includes. Splitting the entry point off into main.fs keeps the
\ play-script reusable across the binary and the test runner.
\
\ The drop sequence is shaped by mzt's lack of `drop-by-name`:
\ `do-drop` calls `pick-carried` which finds the lowest-id carried
\ item. Stick is id 1, ball is id 2, so a drop in the kitchen with
\ both carried drops the stick. We dispose of the stick at the road
\ on the way back (where the ball isn't, so `pick-carried` can only
\ pick the stick) and then drop the ball alone in the kitchen.
\ Different drop order, same world.

include game.fs

: walk-to-stick
    key-n dispatch                       \ hallway
    key-n dispatch                       \ garden
    key-t dispatch ;                     \ take stick

: fetch-ball
    key-n dispatch                       \ road
    key-e dispatch                       \ well (with stick)
    key-t dispatch ;                     \ take ball (stick + ball both carried)

: bring-it-home
    key-w dispatch                       \ road
    key-d dispatch                       \ drop stick at road (lower id wins)
    key-s dispatch                       \ garden
    key-s dispatch                       \ hallway
    key-s dispatch                       \ kitchen
    key-d dispatch ;                     \ drop ball (only thing left) — wins

: play
    walk-to-stick
    fetch-ball
    bring-it-home ;

: report
    won? if
        ." won "
    else
        ." lost "
    then
    ball item-room@ kitchen = if ." (ball at home)" else ." (ball elsewhere)" then
    cr ;
