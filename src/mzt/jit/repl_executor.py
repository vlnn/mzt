from typing import Callable

from mzt.compiler import CompileError, ProgramState, compile_increment
from mzt.ir import ColonDef
from mzt.jit.emitter import JitEmitterError
from mzt.jit.executor import JitExecutor
from mzt.session import Session
from mzt.tokenizer import TokenizerError


class JitReplExecutor:
    def __init__(self, executor_factory: Callable[[], JitExecutor] | None = None):
        self._executor_factory = executor_factory or JitExecutor.open
        self._executor: JitExecutor | None = None
        self._private_state = ProgramState(allow_redefinition=True)
        self._defs_by_name: dict[str, ColonDef] = {}
        self._eval_counter = 0

    def __call__(self, session: Session, expression: str) -> str:
        self._ensure_executor()
        try:
            self._absorb_session_defs(session)
        except (CompileError, TokenizerError) as exc:
            return f"error: {exc}\n"

        eval_name = self._fresh_eval_name()
        try:
            session.feed(f": {eval_name} {expression} ;")
        except (CompileError, TokenizerError) as exc:
            return f"error: {exc}\n"

        try:
            self._absorb_eval(session, eval_name)
        except (CompileError, TokenizerError) as exc:
            return f"error: {exc}\n"

        try:
            self._jit_compile_pending()
        except JitEmitterError as exc:
            return f"error: {exc}\n"
        self._executor.execute_word(eval_name)
        return ""

    def reset(self) -> None:
        if self._executor is not None:
            self._executor.reset()

    def close(self) -> None:
        if self._executor is not None:
            self._executor.close()
            self._executor = None

    @property
    def data_stack(self) -> list[int]:
        if self._executor is None:
            return []
        return self._executor.read_dstack()

    @property
    def return_stack(self) -> list[int]:
        if self._executor is None:
            return []
        return self._executor.read_rstack()

    def _ensure_executor(self) -> None:
        if self._executor is None:
            self._executor = self._executor_factory()

    def _fresh_eval_name(self) -> str:
        name = f"__jit_eval_{self._eval_counter}"
        self._eval_counter += 1
        return name

    def _absorb_session_defs(self, session: Session) -> None:
        for info in session.interactive_defs():
            if info.name in self._defs_by_name:
                continue
            if info.source_text is None:
                continue
            self._absorb_source(info.source_text)

    def _absorb_eval(self, session: Session, eval_name: str) -> None:
        info = session.state.dictionary.get(eval_name)
        if info is None or info.source_text is None:
            return
        self._absorb_source(info.source_text)

    def _absorb_source(self, source_text: str) -> None:
        defs = compile_increment(source_text, state=self._private_state)
        for d in defs:
            self._defs_by_name[d.name] = d

    def _jit_compile_pending(self) -> None:
        for name, colon_def in self._defs_by_name.items():
            if name in self._executor.word_addresses:
                continue
            self._executor.compile(name, colon_def.body)
