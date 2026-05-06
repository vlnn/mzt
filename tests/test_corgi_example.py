from pathlib import Path

import pytest

from mzt.compiler import compile_source
from mzt.dictionary import Dictionary
from mzt.emitter import emit_program
from mzt.ir import ColonDef


CORGI = Path(__file__).parent.parent / "examples" / "corgi"
WORLD = CORGI / "world.fs"
GAME = CORGI / "game.fs"
MAIN = CORGI / "main.fs"
TESTS = CORGI / "tests" / "test_corgi.fs"


@pytest.fixture(scope="module")
def main_defs() -> dict[str, ColonDef]:
    src = MAIN.read_text()
    return {d.name: d for d in compile_source(src, source_path=MAIN)}


@pytest.fixture(scope="module")
def playthrough_defs() -> dict[str, ColonDef]:
    """playthrough.fs is no longer in main.fs's include chain (main now
    runs run-corgi from interactive.fs), so its defs are loaded from
    the playthrough source directly."""
    path = CORGI / "playthrough.fs"
    return {d.name: d for d in compile_source(path.read_text(), source_path=path)}


@pytest.mark.parametrize("relpath", [
    "main.fs",
    "interactive.fs",
    "playthrough.fs",
    "world.fs",
    "game.fs",
    "tests/test_corgi.fs",
    "README.md",
])
def test_corgi_files_exist(relpath):
    assert (CORGI / relpath).is_file(), \
        f"corgi example should ship {relpath}"


def test_main_compiles_and_produces_assembly():
    src = MAIN.read_text()
    defs = compile_source(src, source_path=MAIN)
    asm = emit_program(defs)
    assert "_word_main:" in asm, \
        "corgi main.fs should produce a _word_main label so _main can call into it"


def test_main_defined(main_defs):
    assert "main" in main_defs, "corgi should produce a 'main' word"


@pytest.mark.parametrize("word", [
    "kitchen", "hallway", "garden", "road", "well",
    "bone", "stick", "ball", "carried", "nowhere",
    "here-room",
    "/room", ".exits", ".description",
    "exit-of", "blocked?", "carrying?", "here?", "have-stick?",
    "room-has?", "in-room?",
    "place-items", "init-exits", "connect", "connect-pair",
    "opposite-dir",
    "item-room@", "item-room!",
    "pick-at",
])
def test_world_words_defined(main_defs, word):
    assert word in main_defs, f"world.fs should define {word!r}"


@pytest.mark.parametrize("word", [
    "describe-room", "look-here", "list-inventory",
    "do-north", "do-south", "do-east", "do-west", "try-go",
    "do-take", "do-drop", "do-inventory",
    "do-bark", "do-help", "do-look", "do-quit",
    "won?", "celebrate",
    "dispatch", "lookup-cmd",
    "render", "ansi-clear",
    "reset-game",
    "show-msg", "last-msg", "last-item",
    "item-printers", "msg-printers",
    "cmd-keys", "cmd-actions",
])
def test_game_words_defined(main_defs, word):
    assert word in main_defs, f"game.fs should define {word!r}"


@pytest.mark.parametrize("word", [
    "play", "walk-to-stick", "fetch-ball", "bring-it-home",
    "report",
])
def test_scripted_playthrough_words_defined(playthrough_defs, word):
    assert word in playthrough_defs, \
        f"playthrough.fs should define {word!r}"


@pytest.mark.parametrize("word", [
    "run-corgi", "intro", "closing", "turn",
    "read-line-first", "lower", "ascii-upper?",
    "input-first",
])
def test_interactive_words_defined(main_defs, word):
    """interactive.fs is now in main.fs's include chain; its words
    must be reachable from the interactive build."""
    assert word in main_defs, \
        f"interactive.fs should define {word!r}"


@pytest.mark.parametrize("name", [
    "kitchen", "hallway", "garden", "road", "well",
    "item-loc", "item-homes", "item-printers", "msg-printers",
    "cmd-keys", "cmd-actions",
])
def test_data_arrays_present(main_defs, name):
    """zt's w:/c: array literals become create+allot regions in mzt; the
    arrays should still be defined as named words."""
    assert name in main_defs, f"data array {name!r} should be created"


def test_test_file_compiles_and_lists_test_words():
    src = TESTS.read_text()
    defs = compile_source(src, source_path=TESTS)
    test_words = [d.name for d in defs if d.name.startswith("test-")]
    assert len(test_words) >= 30, \
        f"test_corgi.fs should define at least 30 test- words, found {len(test_words)}"


@pytest.mark.parametrize("expected", [
    "test-start-room-is-kitchen",
    "test-init-exits-bidirectional-kitchen-hallway",
    "test-east-from-road-without-stick-stays-on-road",
    "test-east-from-road-with-stick-reaches-well",
    "test-do-take-bone-puts-it-in-jaws",
    "test-do-drop-puts-bone-in-current-room",
    "test-won-when-ball-rests-in-kitchen",
    "test-dispatch-n-moves-north",
    "test-dispatch-unknown-letter-flags-unknown",
    "test-pick-at-kitchen-finds-bone",
    "test-scripted-playthrough-wins",
])
def test_specific_test_words_present(expected):
    src = TESTS.read_text()
    defs = compile_source(src, source_path=TESTS)
    names = {d.name for d in defs}
    assert expected in names, \
        f"corgi test suite should include {expected!r}"


@pytest.mark.parametrize("test_word", [
    "test-start-room-is-kitchen",
    "test-east-from-road-with-stick-reaches-well",
    "test-scripted-playthrough-wins",
    "test-opposite-dir-n-is-s",
])
def test_synthesised_test_main_compiles_with_single_main(test_word):
    """Regression for the test-harness `: main` collision: when a test
    file includes a module that itself defines `: main`, the harness's
    strip regex (which only sees the test file's own source) leaves both
    definitions in the synthesised program and the compiler errors with
    'main' is already defined. Splitting the playthrough script off into
    playthrough.fs keeps test_corgi.fs's transitive includes free of
    `: main`, and this test locks that property in."""
    from mzt.forth_test_runner import synthesize_test_main
    source = TESTS.read_text()
    program = synthesize_test_main(source, test_word)
    defs = compile_source(program, source_path=TESTS)
    main_defs = [d for d in defs if d.name == "main"]
    assert len(main_defs) == 1, \
        f"synthesised test program for {test_word!r} should define main exactly once, got {len(main_defs)}"


@pytest.mark.parametrize("from_room,to_room,direction", [
    ("kitchen", "hallway", "dir-n"),
    ("hallway", "garden",  "dir-n"),
    ("garden",  "road",    "dir-n"),
    ("road",    "well",    "dir-e"),
])
def test_install_edges_arg_order_is_from_to_dir(main_defs, from_room, to_room, direction):
    """Regression for the install-edges direction bug: connect-pair
    expects ( from to dir -- ) and writes `to` into `from.exits[dir]`.
    Reversing those two arguments wires the world backwards (kitchen's
    south points to hallway, kitchen's north stays blocked) and breaks
    every movement test plus the scripted playthrough. Lock the IR
    shape to match `from to dir connect-pair` for each corridor."""
    from mzt.ir import ColonRef
    body = main_defs["install-edges"].body
    expected = [
        ColonRef(from_room), ColonRef(to_room),
        ColonRef(direction), ColonRef("connect-pair"),
    ]
    assert expected in [list(body[i:i + 4]) for i in range(0, len(body), 4)], \
        (f"install-edges should call connect-pair with "
         f"({from_room} {to_room} {direction}), not the reverse — see "
         f"world.fs and the test-corgi.fs failure mode")
