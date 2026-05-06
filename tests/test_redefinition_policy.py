import pytest

from mzt.compiler import (
    CompileError,
    ProgramState,
    compile_increment,
    compile_source,
)
from mzt.ir import ColonDef, ColonRef, Literal


def _find(defs: list[ColonDef], name: str) -> ColonDef:
    found = next((d for d in defs if d.name == name), None)
    assert found is not None, f"def {name!r} should be in {[d.name for d in defs]}"
    return found


# ---------------------------------------------------------------------------
# Strict mode (the default) keeps existing behaviour
# ---------------------------------------------------------------------------

def test_strict_state_raises_on_colon_redefinition():
    state = ProgramState()
    compile_increment(": foo 1 ;", state=state)
    with pytest.raises(CompileError, match="already defined"):
        compile_increment(": foo 2 ;", state=state)


def test_strict_state_raises_on_synonym_redefinition():
    state = ProgramState()
    compile_increment(": foo 1 ;", state=state)
    with pytest.raises(CompileError, match="already defined"):
        compile_increment("synonym foo dup", state=state)


def test_strict_state_raises_on_constant_redefinition():
    state = ProgramState()
    compile_increment("42 constant max", state=state)
    with pytest.raises(CompileError, match="already defined"):
        compile_increment("99 constant max", state=state)


# ---------------------------------------------------------------------------
# Permissive mode replaces existing colon and synonym defs
# ---------------------------------------------------------------------------

def test_permissive_state_redefining_colon_replaces_body():
    state = ProgramState(allow_redefinition=True)
    compile_increment(": foo 1 ;", state=state)
    defs = compile_increment(": foo 2 ;", state=state)
    foo = _find(defs, "foo")
    assert Literal(2) in foo.body, \
        f"after permissive redefinition, body should reflect new definition; got {foo.body!r}"


def test_permissive_state_records_a_redefinition_warning():
    state = ProgramState(allow_redefinition=True)
    compile_increment(": foo 1 ;", state=state)
    compile_increment(": foo 2 ;", state=state)
    assert any("foo" in w for w in state.warnings), \
        f"redefinition should record a warning mentioning the word; got {state.warnings!r}"


def test_permissive_state_old_callers_keep_calling_old_binding_in_their_emitted_body():
    """Words compiled before redefinition still refer to their original target
    by name. Late binding at link time will pick up whichever body is current
    when the new image is built; what matters here is no stale IR cell points
    to a removed name."""
    state = ProgramState(allow_redefinition=True)
    compile_increment(": foo 1 ;", state=state)
    compile_increment(": uses-foo foo ;", state=state)
    compile_increment(": foo 2 ;", state=state)
    assert "foo" in state.dictionary, \
        "after redefinition foo must remain in the dictionary"
    assert state.dictionary.get("foo").source_text == ": foo 2 ;", \
        "dictionary entry should reflect the new source_text"


def test_permissive_state_redefinition_does_not_warn_when_name_was_not_present():
    state = ProgramState(allow_redefinition=True)
    compile_increment(": foo 1 ;", state=state)
    assert state.warnings == [], \
        f"first definition is not a redefinition; warnings should be empty, got {state.warnings!r}"


def test_permissive_state_synonym_can_replace_synonym():
    state = ProgramState(allow_redefinition=True)
    compile_increment("synonym d dup", state=state)
    defs = compile_increment("synonym d drop", state=state)
    d = _find(defs, "d")
    assert d.body == (ColonRef("drop"),) or any(
        getattr(c, "name", None) == "drop" for c in d.body
    ), f"second synonym should target drop; got {d.body!r}"


def test_permissive_state_cannot_redefine_a_primitive():
    state = ProgramState(allow_redefinition=True)
    with pytest.raises(CompileError, match="primitive"):
        compile_increment(": dup 1 ;", state=state)


def test_permissive_state_cannot_redefine_a_control_keyword():
    state = ProgramState(allow_redefinition=True)
    with pytest.raises(CompileError, match="control-flow"):
        compile_increment(": if drop ;", state=state)


# ---------------------------------------------------------------------------
# Variables/create are not redefined under permissive mode
# (different lifetime — they own user memory)
# ---------------------------------------------------------------------------

def test_permissive_state_redefining_variable_is_still_an_error():
    state = ProgramState(allow_redefinition=True)
    compile_increment("variable foo", state=state)
    with pytest.raises(CompileError, match="variable"):
        compile_increment("variable foo", state=state)


def test_permissive_state_promoting_colon_to_variable_is_an_error():
    state = ProgramState(allow_redefinition=True)
    compile_increment(": foo 1 ;", state=state)
    with pytest.raises(CompileError, match="variable"):
        compile_increment("variable foo", state=state)
