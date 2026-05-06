\ tests/test_corgi.fs — port of zt's examples/corgi/tests/test_corgi.fs.
\ Each `: test-*` colon definition is one pytest item via conftest.py.
\
\ Most of zt's tests survive untouched because they only touch
\ behaviour, not syntax. The ones that needed adapting:
\ - `lower` is in zt's game.fs, dropped here (no read-line so no need).
\ - `print-help`-mention assertions live in test_corgi.py over there;
\   here they'd need stdout capture which the Forth-side harness
\   doesn't expose. Skipped without loss.

include ../../../tests/forth/test-lib.fs
include ../playthrough.fs


\ ─── starting state ───────────────────────────────────────────────────

: test-start-room-is-kitchen
    reset-game  here-room @  kitchen assert-eq ;

: test-bone-starts-in-kitchen
    reset-game  bone item-room@  kitchen assert-eq ;

: test-stick-starts-in-garden
    reset-game  stick item-room@  garden assert-eq ;

: test-ball-starts-in-well
    reset-game  ball item-room@  well assert-eq ;


\ ─── exits wired correctly ────────────────────────────────────────────

: test-init-exits-wires-kitchen-north
    reset-game  kitchen dir-n exit-of  hallway assert-eq ;

: test-init-exits-wires-kitchen-east-blocked
    reset-game  kitchen dir-e exit-of  -1 assert-eq ;

: test-init-exits-bidirectional-kitchen-hallway
    reset-game
    kitchen dir-n exit-of  hallway assert-eq
    hallway dir-s exit-of  kitchen assert-eq ;

: test-init-exits-road-east-to-well
    reset-game  road dir-e exit-of  well assert-eq ;


\ ─── basic movement ───────────────────────────────────────────────────

: test-do-north-from-kitchen
    reset-game  do-north  here-room @  hallway assert-eq ;

: test-do-east-from-kitchen-blocked-and-flagged
    reset-game  do-east  last-msg @  msg-no-exit assert-eq ;

: test-walk-to-road
    reset-game  do-north do-north do-north
    here-room @  road assert-eq ;


\ ─── road→well stick gating ───────────────────────────────────────────

: test-east-from-road-without-stick-stays-on-road
    reset-game  do-north do-north do-north  do-east
    here-room @  road assert-eq ;

: test-east-from-road-without-stick-flags-too-scary
    reset-game  do-north do-north do-north  do-east
    last-msg @  msg-too-scary assert-eq ;

: test-east-from-road-with-stick-reaches-well
    reset-game  do-north do-north
    do-take  do-north  do-east
    here-room @  well assert-eq ;


\ ─── take and drop ────────────────────────────────────────────────────

: test-do-take-bone-puts-it-in-jaws
    reset-game  do-take
    bone item-room@  carried assert-eq ;

: test-do-take-bone-flags-took
    reset-game  do-take
    last-msg @  msg-took assert-eq ;

: test-do-drop-puts-bone-in-current-room
    reset-game  do-take  do-drop
    bone item-room@  kitchen assert-eq ;

: test-do-drop-flags-dropped
    reset-game  do-take  do-drop
    last-msg @  msg-dropped assert-eq ;

: test-do-take-empty-flags-nothing-here
    reset-game  do-take  do-take
    last-msg @  msg-nothing-here assert-eq ;

: test-do-drop-empty-flags-jaws-empty
    reset-game  do-drop
    last-msg @  msg-jaws-empty assert-eq ;


\ ─── win condition ────────────────────────────────────────────────────

: test-not-won-at-start
    reset-game  won?  assert-false ;

: test-not-won-while-carrying-ball-in-kitchen
    reset-game  carried ball item-room!
    won?  assert-false ;

: test-won-when-ball-rests-in-kitchen
    reset-game  kitchen ball item-room!
    won?  assert-true ;


\ ─── blocked? sentinel ────────────────────────────────────────────────

: test-blocked-flag-on-minus-one
    -1 blocked?  assert-true ;

: test-blocked-flag-false-on-real-room
    reset-game  kitchen blocked?  assert-false ;


\ ─── command-state words ──────────────────────────────────────────────

: test-do-quit-sets-game-over
    reset-game  do-quit
    game-over @  1 assert-eq ;

: test-do-inventory-sets-show-inv-flag
    reset-game  do-inventory
    show-inv? @  1 assert-eq ;

: test-do-help-flags-help
    reset-game  do-help
    last-msg @  msg-help assert-eq ;

: test-do-bark-flags-bark
    reset-game  do-bark
    last-msg @  msg-bark assert-eq ;


\ ─── dispatch ────────────────────────────────────────────────────────

: test-dispatch-h-fires-help
    reset-game  104 dispatch
    last-msg @  msg-help assert-eq ;

: test-dispatch-question-mark-fires-help
    reset-game  63 dispatch
    last-msg @  msg-help assert-eq ;

: test-dispatch-empty-fires-quiet
    reset-game  0 dispatch
    last-msg @  msg-quiet assert-eq ;

: test-dispatch-unknown-letter-flags-unknown
    reset-game  122 dispatch
    last-msg @  msg-unknown assert-eq ;

: test-dispatch-n-moves-north
    reset-game  key-n dispatch
    here-room @  hallway assert-eq ;

: test-dispatch-t-takes-bone-in-kitchen
    reset-game  key-t dispatch
    bone item-room@  carried assert-eq ;


\ ─── direction algebra ───────────────────────────────────────────────

: test-opposite-dir-n-is-s
    dir-n opposite-dir  dir-s assert-eq ;

: test-opposite-dir-s-is-n
    dir-s opposite-dir  dir-n assert-eq ;

: test-opposite-dir-e-is-w
    dir-e opposite-dir  dir-w assert-eq ;

: test-opposite-dir-w-is-e
    dir-w opposite-dir  dir-e assert-eq ;


\ ─── pick-at ─────────────────────────────────────────────────────────

: test-pick-at-kitchen-finds-bone
    reset-game  kitchen pick-at  bone assert-eq ;

: test-pick-at-hallway-empty
    reset-game  hallway pick-at  -1 assert-eq ;

: test-pick-at-carried-after-take-finds-bone
    reset-game  do-take  carried pick-at  bone assert-eq ;


\ ─── full winning playthrough ─────────────────────────────────────────

: test-scripted-playthrough-wins
    reset-game
    play
    won?  assert-true ;

: test-scripted-playthrough-ball-ends-in-kitchen
    reset-game
    play
    ball item-room@  kitchen assert-eq ;
