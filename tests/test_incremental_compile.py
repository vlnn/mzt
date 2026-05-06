from pathlib import Path

import pytest

from mzt.compiler import (
    CompileError,
    ProgramState,
    compile_increment,
    compile_source,
)
from mzt.ir import ColonDef, ColonRef


def _names(defs: list[ColonDef]) -> set[str]:
    return {d.name for d in defs}


# ---------------------------------------------------------------------------
# State carried across calls
# ---------------------------------------------------------------------------

def test_program_state_can_be_constructed_with_no_arguments():
    state = ProgramState()
    assert len(state.dictionary) == 0, \
        "fresh ProgramState should start with an empty dictionary"


def test_compile_increment_returns_only_the_new_defs():
    state = ProgramState()
    first = compile_increment(": foo 1 ;", state=state)
    second = compile_increment(": bar 2 ;", state=state)
    assert _names(first) == {"foo"}, \
        "first increment should return only foo"
    assert _names(second) == {"bar"}, \
        "second increment should return only the new def, not the cumulative set"


def test_dictionary_accumulates_across_increments():
    state = ProgramState()
    compile_increment(": foo 1 ;", state=state)
    compile_increment(": bar 2 ;", state=state)
    assert "foo" in state.dictionary, \
        "after two increments, foo should still be registered"
    assert "bar" in state.dictionary, \
        "after two increments, bar should be registered"


def test_increment_can_call_word_defined_in_previous_increment():
    state = ProgramState()
    compile_increment(": dbl 2 * ;", state=state)
    defs = compile_increment(": quad dbl dbl ;", state=state)
    quad = next(d for d in defs if d.name == "quad")
    assert ColonRef("dbl") in quad.body, \
        "second increment should resolve 'dbl' from the persistent dictionary"


def test_increment_redefining_existing_word_in_strict_mode_raises():
    state = ProgramState()
    compile_increment(": foo 1 ;", state=state)
    with pytest.raises(CompileError, match="already defined"):
        compile_increment(": foo 2 ;", state=state)


def test_user_memory_bump_pointer_persists_across_increments():
    state = ProgramState()
    compile_increment("variable foo", state=state)
    bump_after_first = state.bump
    compile_increment("variable bar", state=state)
    assert state.bump > bump_after_first, \
        "second variable should claim more user memory; bump pointer must persist"


def test_resolver_dedup_persists_across_increments(tmp_path: Path):
    helper = tmp_path / "helper.fs"
    helper.write_text(": helped 99 ;")
    state = ProgramState()
    compile_increment("include helper.fs", state=state, include_dirs=[tmp_path])
    second = compile_increment("include helper.fs : main helped ;", state=state, include_dirs=[tmp_path])
    helped_defs = [d for d in second if d.name == "helped"]
    assert helped_defs == [], \
        "second include of the same file should be a no-op; helped should not appear in the new defs"
    assert "helped" in state.dictionary, \
        "but helped should still be callable from main because it's in the persistent dictionary"


# ---------------------------------------------------------------------------
# Backward compat: compile_source unchanged when no state passed
# ---------------------------------------------------------------------------

def test_compile_source_still_works_with_no_state_argument():
    defs = compile_source(": foo 1 ;")
    assert _names(defs) == {"foo"}, \
        "existing compile_source signature must still work without a state argument"


def test_two_independent_compile_source_calls_have_independent_state():
    first = compile_source(": foo 1 ;")
    second = compile_source(": foo 2 ;")
    assert _names(first) == {"foo"}, \
        "compile_source without state should not see foo from a previous call"
    assert _names(second) == {"foo"}, \
        "redefinition between independent compile_source calls must be allowed"
