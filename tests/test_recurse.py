import pytest

from mzt.compiler import CompileError, compile_source
from mzt.ir import ColonRef, Literal, PrimRef


def _body(source: str):
    [d] = compile_source(source)
    return d.body


def test_recurse_emits_colon_ref_to_self():
    body = _body(": fact dup 1 = if drop 1 else dup 1 - recurse * then ;")
    assert ColonRef("fact") in body, \
        "recurse inside ': fact ... ;' should emit a ColonRef to 'fact'"


def test_recurse_outside_colon_definition_raises():
    # recurse is a control word that only makes sense inside a colon body.
    # A bare `recurse` at top level isn't even reachable — top-level rejects
    # unknown words. This test confirms the path produces a CompileError, not
    # a silent ColonRef("?").
    with pytest.raises(CompileError):
        compile_source("recurse")


def test_recurse_resolves_to_current_definition_not_a_previous_one():
    [_foo, bar] = compile_source(": foo 1 ; : bar 2 recurse ;")
    assert ColonRef("bar") in bar.body, \
        "recurse inside ': bar ;' should resolve to bar, not the previous foo definition"
    assert ColonRef("foo") not in bar.body, \
        "recurse must never resolve to a previously-defined word"


def test_recurse_inside_loop_body_compiles():
    body = _body(": foo 5 0 do recurse loop ;")
    assert ColonRef("foo") in body, \
        "recurse inside a do/loop should still resolve to the enclosing colon definition"


def test_recurse_inside_if_then_compiles():
    body = _body(": foo 1 if recurse then ;")
    assert ColonRef("foo") in body, \
        "recurse inside if/then should resolve normally"


@pytest.mark.parametrize(
    "name",
    ["fact", "fib", "ackermann", "deep-thought"],
)
def test_recurse_picks_up_the_current_word_name(name):
    src = f": {name} recurse ;"
    [d] = compile_source(src)
    assert ColonRef(name) in d.body, \
        f"recurse inside ': {name} ;' should emit ColonRef({name!r})"
