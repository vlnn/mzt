from pathlib import Path

import pytest

from mzt.compiler import compile_source
from mzt.emitter import emit_program
from mzt.ir import Branch, ColonRef, Label, Literal, PrimRef


EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def fib_defs():
    path = EXAMPLES / "bench-fib.fs"
    return {d.name: d for d in compile_source(path.read_text(), source_path=path)}


@pytest.fixture(scope="module")
def pi_defs():
    path = EXAMPLES / "bench-pi.fs"
    return {d.name: d for d in compile_source(path.read_text(), source_path=path)}


@pytest.mark.parametrize("name", ["bench-fib.fs", "bench-pi.fs"])
def test_benchmark_source_compiles_to_assembly(name):
    path = EXAMPLES / name
    defs = compile_source(path.read_text(), source_path=path)
    asm = emit_program(defs)
    assert "_word_main:" in asm, \
        f"{name} should produce a _word_main label so _main can call into it"


def test_fib_defines_only_fib_and_main(fib_defs):
    assert set(fib_defs) == {"fib", "main"}, \
        "bench-fib.fs should produce exactly fib and main, no stray defs from include"


def test_fib_main_calls_fib_with_35(fib_defs):
    body = fib_defs["main"].body
    assert Literal(35) in body, "fib benchmark should drive fib with n=35"
    assert ColonRef("fib") in body, "fib benchmark's main should call fib"
    assert PrimRef(".") in body, "fib benchmark should print the result"


def test_fib_body_contains_recursive_self_reference(fib_defs):
    body = fib_defs["fib"].body
    recursive_calls = [c for c in body if c == ColonRef("fib")]
    assert len(recursive_calls) == 2, \
        "naive fib body should call itself exactly twice (fib n-1 and fib n-2)"


def test_fib_body_uses_conditional_branch(fib_defs):
    body = fib_defs["fib"].body
    has_conditional = any(isinstance(c, Branch) and c.conditional for c in body)
    has_label = any(isinstance(c, Label) for c in body)
    assert has_conditional and has_label, \
        "fib body should compile if/then to a conditional Branch plus Label"


def test_pi_pulls_in_stdlib_via_include(pi_defs):
    assert "/" in pi_defs, \
        "bench-pi.fs uses 'include core.fs', so / from stdlib should be present"
    assert "2dup" in pi_defs, \
        "include core.fs should pull all stdlib defs in (this is what tree-shaking will fix)"


def test_pi_main_drives_pi_loop_with_million_terms(pi_defs):
    body = pi_defs["main"].body
    assert Literal(1000000) in body, \
        "pi benchmark should run 1M Leibniz terms in the default config"
    assert Literal(10000000) in body, \
        "pi benchmark should use scale=10^7"
    assert ColonRef("pi-loop") in body, \
        "pi main should call pi-loop"


def test_pi_loop_uses_counted_loop_primitives(pi_defs):
    body = pi_defs["pi-loop"].body
    prim_names = {c.name for c in body if isinstance(c, PrimRef)}
    assert "(do)" in prim_names, "pi-loop should compile do/loop to (do)"
    assert "(loop)" in prim_names, "pi-loop should compile do/loop to (loop)"
    assert "i" in prim_names, "pi-loop body should read the loop index via i"


def test_pi_term_does_arithmetic_and_signed_negation(pi_defs):
    body = pi_defs["pi-term"].body
    prim_names = [c.name for c in body if isinstance(c, PrimRef)]
    assert "*" in prim_names, "pi-term computes 2i+1 with *"
    assert "+" in prim_names, "pi-term computes 2i+1 with + and accumulates with +"
    assert "and" in prim_names, "pi-term extracts parity bit with 1 and"
    assert "negate" in prim_names, \
        "pi-term flips the sign of every other term via negate"


@pytest.mark.parametrize("name", ["bench-fib.fs", "bench-pi.fs"])
def test_benchmark_source_has_no_stray_unknown_word_refs(name):
    """Every ColonRef in the IR must resolve to a defined word. Catches
    typos and the stack-effect-comment-with-parens trap (where ')' would
    otherwise leak through as an unknown-word ColonRef)."""
    path = EXAMPLES / name
    defs = compile_source(path.read_text(), source_path=path)
    defined_names = {d.name for d in defs}
    referenced = {
        c.name
        for d in defs
        for c in d.body
        if isinstance(c, ColonRef)
    }
    unresolved = referenced - defined_names
    assert not unresolved, \
        f"{name} has ColonRef(s) to undefined words: {sorted(unresolved)}"
