import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from mzt.builder import build_source_text
from mzt.session import Session


STATE_START_MARKER = "__MZT_STATE_BEGIN__"
STATE_END_MARKER = "__MZT_STATE_END__"


class StackError(Exception):
    pass


@dataclass
class _ParsedState:
    data_stack: list[int] = field(default_factory=list)
    return_stack: list[int] = field(default_factory=list)
    variables: dict[str, int] = field(default_factory=dict)


class ClangExecutor:

    def __init__(self) -> None:
        self.data_stack: list[int] = []
        self.return_stack: list[int] = []
        self.variables: dict[str, int] = {}

    def reset(self) -> None:
        self.data_stack = []
        self.return_stack = []
        self.variables = {}

    def __call__(self, session: Session, expression: str) -> str:
        variable_names = _variable_names(session)
        program = _stitch_program(
            session,
            prelude=render_prelude(
                data_stack=self.data_stack,
                return_stack=self.return_stack,
                variables=self.variables,
            ),
            expression=expression,
            epilogue=render_state_epilogue(variable_names=variable_names),
        )
        with tempfile.TemporaryDirectory(prefix="mzt-repl-") as tmpdir:
            binary_path = Path(tmpdir) / "expr"
            build_source_text(
                program,
                binary_path,
                include_dirs=list(session.include_dirs) or None,
            )
            result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        if result.returncode != 0:
            self.reset()
            return result.stdout + result.stderr
        try:
            user_output, state = parse_state_dump(result.stdout)
        except StackError:
            self.reset()
            return result.stdout
        self.data_stack = state.data_stack
        self.return_stack = state.return_stack
        self.variables = {**self.variables, **state.variables}
        return user_output


def _variable_names(session: Session) -> list[str]:
    return [
        name for name in session.state.dictionary
        if (info := session.state.dictionary.get(name)) is not None
        and info.kind == "variable"
    ]


def render_prelude(
    *,
    data_stack: list[int],
    return_stack: list[int],
    variables: dict[str, int],
) -> str:
    parts: list[str] = []
    parts.extend(f"{value} {name} !" for name, value in variables.items())
    parts.extend(f"{value} >r" for value in return_stack)
    if data_stack:
        parts.append(" ".join(str(v) for v in data_stack))
    return " ".join(parts)


def render_state_epilogue(*, variable_names: list[str]) -> str:
    pieces = [
        f'." {STATE_START_MARKER}" cr',
        "__dump-stacks",
        f'." VARS {len(variable_names)}" cr',
    ]
    for name in variable_names:
        pieces.append(f'." {name} " {name} @ .')
    pieces.append(f'." {STATE_END_MARKER}" cr')
    return " ".join(pieces)


def parse_state_dump(raw: str) -> tuple[str, _ParsedState]:
    start = raw.find(STATE_START_MARKER)
    end = raw.find(STATE_END_MARKER)
    if start < 0 or end < 0:
        raise StackError("missing state dump markers in program output")
    user_output = raw[:start]
    block = raw[start + len(STATE_START_MARKER):end].strip("\n")
    return user_output, _parse_state_block(block)


def _parse_state_block(block: str) -> _ParsedState:
    lines = block.split("\n")
    state = _ParsedState()
    i = 0
    while i < len(lines):
        header = lines[i].strip()
        if header.startswith("DSTACK "):
            count = int(header.split()[1])
            state.data_stack = [int(x) for x in lines[i + 1 : i + 1 + count]]
            i += 1 + count
            continue
        if header.startswith("RSTACK "):
            count = int(header.split()[1])
            state.return_stack = [int(x) for x in lines[i + 1 : i + 1 + count]]
            i += 1 + count
            continue
        if header.startswith("VARS "):
            count = int(header.split()[1])
            for var_line in lines[i + 1 : i + 1 + count]:
                name, value = var_line.rsplit(maxsplit=1)
                state.variables[name.strip()] = int(value)
            i += 1 + count
            continue
        i += 1
    return state


def _stitch_program(
    session: Session,
    *,
    prelude: str,
    expression: str,
    epilogue: str,
) -> str:
    parts: list[str] = []
    for info in session.interactive_defs():
        if info.source_text is not None:
            parts.append(info.source_text)
    main_body = " ".join(p for p in (prelude, expression, epilogue) if p)
    parts.append(f": main {main_body} ;")
    return "\n".join(session.include_lines + parts) + "\n"
