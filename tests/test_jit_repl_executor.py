import sys
from typing import Callable

import pytest

from mzt.ir import ColonDef, ColonRef, Literal, PrimRef
from mzt.jit.repl_executor import JitReplExecutor
from mzt.session import Session


class _FakeJitExecutor:
    def __init__(self):
        self.word_addresses: dict[str, int] = {}
        self.compiled_bodies: dict[str, list] = {}
        self.executed: list[str] = []
        self.x19_at_top = True
        self.x20_at_top = True
        self.dstack: list[int] = []
        self.rstack: list[int] = []
        self._next_addr = 0x1000_0000
        self.closed = False
        self.reset_count = 0

    def compile(self, name: str, cells) -> int:
        from mzt.ir import ColonRef
        from mzt.jit.emitter import JitEmitterError

        cells_list = list(cells)
        addr = self._next_addr
        self._next_addr += 0x100
        self.word_addresses[name] = addr
        try:
            for cell in cells_list:
                if isinstance(cell, ColonRef) and cell.name not in self.word_addresses:
                    raise JitEmitterError(
                        f"colon word {cell.name!r} not yet emitted; its address is unknown"
                    )
        except Exception:
            del self.word_addresses[name]
            raise
        self.compiled_bodies[name] = cells_list
        return addr

    def execute(self, addr: int) -> None:
        for name, candidate in self.word_addresses.items():
            if candidate == addr:
                self.executed.append(name)
                return
        raise KeyError(addr)

    def execute_word(self, name: str) -> None:
        self.executed.append(name)

    def reset(self) -> None:
        self.reset_count += 1
        self.dstack.clear()
        self.rstack.clear()

    def read_dstack(self) -> list[int]:
        return list(self.dstack)

    def read_rstack(self) -> list[int]:
        return list(self.rstack)

    def close(self) -> None:
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def fake_executor() -> _FakeJitExecutor:
    return _FakeJitExecutor()


@pytest.fixture
def repl(fake_executor) -> JitReplExecutor:
    return JitReplExecutor(executor_factory=lambda: fake_executor)


def _interactive_def_names(session: Session) -> list[str]:
    return [info.name for info in session.interactive_defs()]


def test_evaluate_simple_expression_compiles_and_executes(repl, fake_executor):
    session = Session()
    repl(session, "2 3 +")
    assert any(name.startswith("__jit_eval") for name in fake_executor.executed), \
        "evaluating an expression should JIT-compile a synthetic word and execute it"


def test_evaluate_creates_a_unique_synthetic_name_each_call(repl, fake_executor):
    session = Session()
    repl(session, "1")
    repl(session, "2")
    eval_names = [n for n in fake_executor.executed if n.startswith("__jit_eval")]
    assert len(eval_names) == 2 and eval_names[0] != eval_names[1], \
        "consecutive expressions must get distinct synthetic names so old IR isn't re-used"


def test_evaluate_after_definition_jit_compiles_the_definition(repl, fake_executor):
    session = Session()
    session.feed(": double dup + ;")
    repl(session, "5 double")
    assert "double" in fake_executor.word_addresses, \
        "before executing a word that uses 'double', 'double' itself must be JIT-compiled"


def test_evaluate_compiles_definitions_in_feed_order(repl, fake_executor):
    session = Session()
    session.feed(": one 1 ;")
    session.feed(": two one one + ;")
    repl(session, "two")
    addr_one = fake_executor.word_addresses["one"]
    addr_two = fake_executor.word_addresses["two"]
    assert addr_one < addr_two, \
        "'one' must be compiled before 'two' since 'two' calls into it"


def test_evaluate_does_not_recompile_already_jitted_words(repl, fake_executor):
    session = Session()
    session.feed(": foo 7 ;")
    repl(session, "foo")
    address_first = fake_executor.word_addresses["foo"]
    repl(session, "foo")
    address_second = fake_executor.word_addresses["foo"]
    assert address_first == address_second, \
        "an already-JIT'd word must keep its address — no recompile, no aliased copies"


def test_evaluate_returns_empty_string_on_success(repl):
    session = Session()
    result = repl(session, "1 2 +")
    assert result == "", \
        "JIT'd primitives write to fd 1 directly; the executor returns no extra string"


def test_evaluate_surfaces_compile_error_as_message(repl):
    session = Session()
    result = repl(session, "no-such-word")
    assert "no-such-word" in result and "error" in result.lower(), \
        "an unknown word during compile should surface as a non-empty error message"


def test_reset_resets_underlying_executor_but_keeps_compiled_words(repl, fake_executor):
    session = Session()
    session.feed(": foo 1 ;")
    repl(session, "foo")
    repl.reset()
    assert fake_executor.reset_count == 1, "reset should delegate to the underlying executor"
    assert "foo" in fake_executor.word_addresses, \
        "reset should NOT clear word_addresses; the JIT region still holds the bytes"


def test_data_stack_property_reads_from_executor(repl, fake_executor):
    repl(Session(), "1")
    fake_executor.dstack = [10, 20]
    assert repl.data_stack == [10, 20], \
        "data_stack should return whatever the underlying executor's read_dstack returns"


def test_return_stack_property_reads_from_executor(repl, fake_executor):
    repl(Session(), "1")
    fake_executor.rstack = [99]
    assert repl.return_stack == [99], \
        "return_stack should mirror the executor's read_rstack"


def test_data_stack_before_first_evaluate_is_empty(repl):
    assert repl.data_stack == [], \
        "before any evaluate call, the JIT executor isn't open yet — stack is empty"


def test_executor_is_opened_lazily(fake_executor):
    factory_calls = []

    def factory():
        factory_calls.append(1)
        return fake_executor

    repl = JitReplExecutor(executor_factory=factory)
    assert factory_calls == [], "constructing the REPL must not open the executor"
    repl(Session(), "1")
    assert factory_calls == [1], "first call should open the executor exactly once"
    repl(Session(), "2")
    assert factory_calls == [1], "subsequent calls must reuse the same open executor"


def test_close_closes_underlying_executor(repl, fake_executor):
    repl(Session(), "1")
    repl.close()
    assert fake_executor.closed, "close should propagate to the underlying executor"


def test_close_is_safe_when_executor_was_never_opened():
    repl = JitReplExecutor(executor_factory=lambda: pytest.fail("must not be called"))
    repl.close()


def test_definitions_with_two_levels_of_dependency_compile_in_order(repl, fake_executor):
    session = Session()
    session.feed(": a 1 ;")
    session.feed(": b a 2 + ;")
    session.feed(": c b 3 + ;")
    repl(session, "c")

    addr_a = fake_executor.word_addresses["a"]
    addr_b = fake_executor.word_addresses["b"]
    addr_c = fake_executor.word_addresses["c"]
    assert addr_a < addr_b < addr_c, \
        "transitive dependencies must all be JIT'd before their callers"


def test_evaluate_with_no_prior_definitions(repl, fake_executor):
    session = Session()
    repl(session, "42 .")
    assert any(n.startswith("__jit_eval") for n in fake_executor.word_addresses), \
        "a fresh session with just an expression should still produce one synthetic word"


def test_compiled_word_body_contains_expected_ir_cells(repl, fake_executor):
    session = Session()
    session.feed(": triple dup dup + + ;")
    repl(session, "5 triple")
    triple_body = fake_executor.compiled_bodies["triple"]
    cell_kinds = [type(c).__name__ for c in triple_body]
    assert "PrimRef" in cell_kinds, \
        "'triple' body must contain primitive references like dup and +"


@pytest.mark.skipif(sys.platform != "darwin", reason="needs real JIT host")
def test_real_jit_evaluates_simple_arithmetic():
    repl = JitReplExecutor()
    try:
        session = Session()
        repl(session, "2 3 +")
        assert repl.data_stack == [5], \
            "JIT-evaluating '2 3 +' should leave 5 on the data stack"
    finally:
        repl.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="needs real JIT host")
def test_real_jit_evaluates_user_definition():
    repl = JitReplExecutor()
    try:
        session = Session()
        session.feed(": double dup + ;")
        repl(session, "21 double")
        assert repl.data_stack == [42], \
            "JIT'd 'double' word should produce 42 from input 21"
    finally:
        repl.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="needs real JIT host")
def test_real_jit_state_persists_across_evaluate_calls():
    repl = JitReplExecutor()
    try:
        session = Session()
        repl(session, "10")
        repl(session, "20 +")
        assert repl.data_stack == [30], \
            "10 then 20 + in separate calls should accumulate on the same persistent stack"
    finally:
        repl.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="needs real JIT host")
def test_real_jit_reset_clears_data_stack():
    repl = JitReplExecutor()
    try:
        session = Session()
        repl(session, "1 2 3")
        assert repl.data_stack == [1, 2, 3], "preconditions"
        repl.reset()
        assert repl.data_stack == [], \
            "reset should put x19 back at dstack_top, making the stack empty"
    finally:
        repl.close()
