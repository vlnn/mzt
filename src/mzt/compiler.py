from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from mzt.control_stack import ControlStack, ControlStackError
from mzt.dictionary import Dictionary
from mzt.include_resolver import IncludeNotFound, IncludeResolver
from mzt.ir import Addr, Branch, Cell, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit, WordAddr
from mzt.primitives import is_primitive
from mzt.tokenizer import Token, TokenKind, tokenize


CELL_BYTES = 8


class CompileError(Exception):
    pass


@dataclass
class _LabelGen:
    next_id: int = 0

    def fresh(self) -> int:
        i = self.next_id
        self.next_id += 1
        return i


@dataclass(frozen=True)
class _DoFrame:
    back_label: int
    exit_label: int
    saved_r_depth: int


@dataclass
class _BodyState:
    cells: list[Cell] = field(default_factory=list)
    cf_stack: ControlStack = field(default_factory=ControlStack)
    labels: _LabelGen = field(default_factory=_LabelGen)
    r_depth: int = 0
    current_name: str = ""


@dataclass
class _ProgramState:
    bump: int = 0
    dictionary: Dictionary = field(default_factory=Dictionary)
    labels: _LabelGen = field(default_factory=_LabelGen)
    synthetic_defs: list[ColonDef] = field(default_factory=list)
    next_noname_id: int = 0
    resolver: IncludeResolver = field(default_factory=IncludeResolver)
    current_source_path: "Path | None" = None
    source_texts: dict[str, str] = field(default_factory=dict)

    def claim_address(self, size: int) -> int:
        offset = self.bump
        self.bump += size
        return offset

    def fresh_noname_name(self) -> str:
        name = f"__noname_{self.next_noname_id}"
        self.next_noname_id += 1
        return name

    def slice_source(self, start: Token, end: Token) -> str | None:
        if start.source != end.source:
            return None
        text = self.source_texts.get(start.source)
        if text is None:
            return None
        return text[start.start_offset:end.end_offset]


def compile_source(
    source: str,
    *,
    source_path: "Path | None" = None,
    include_dirs: "list[Path] | None" = None,
) -> list[ColonDef]:
    source_name = str(source_path) if source_path else "<input>"
    return compile_tokens(
        tokenize(source, source=source_name),
        source_path=source_path,
        include_dirs=include_dirs,
        source_text=source,
    )


def compile_tokens(
    tokens: list[Token],
    *,
    source_path: "Path | None" = None,
    include_dirs: "list[Path] | None" = None,
    source_text: str | None = None,
) -> list[ColonDef]:
    cursor = _PeekableTokens(tokens)
    state = _ProgramState(
        resolver=IncludeResolver(include_dirs=include_dirs),
        current_source_path=source_path,
    )
    if source_text is not None:
        source_name = str(source_path) if source_path else "<input>"
        state.source_texts[source_name] = source_text
    if source_path is not None:
        state.resolver.mark_seen(Path(source_path).resolve())
    top_level = list(_parse_top_level(cursor, state))
    return top_level + state.synthetic_defs


def _parse_top_level(cursor: "_PeekableTokens", state: _ProgramState) -> Iterator[ColonDef]:
    while not cursor.eof():
        token = cursor.next()
        if token.kind == TokenKind.COLON:
            yield _parse_colon(cursor, token, state)
            continue
        if token.kind == TokenKind.WORD and token.value == "variable":
            yield _parse_variable(cursor, token, state)
            continue
        if token.kind == TokenKind.WORD and token.value == "create":
            yield _parse_create(cursor, token, state)
            continue
        if token.kind == TokenKind.WORD and token.value == "allot":
            raise CompileError(
                f"line {token.line}: 'allot' without a preceding 'create' definition"
            )
        if token.kind == TokenKind.WORD and token.value == "constant":
            raise CompileError(
                f"line {token.line}: 'constant' without a preceding integer literal "
                "(use as ': <num> constant <name>')"
            )
        if token.kind == TokenKind.NUMBER and _next_is_constant(cursor):
            keyword = cursor.next()
            yield _parse_constant(cursor, token, keyword, state)
            continue
        if token.kind == TokenKind.WORD and token.value == ":noname":
            raise CompileError(
                f"line {token.line}: ':noname' only makes sense inside a colon "
                "definition where its address can be pushed onto the data stack"
            )
        if token.kind == TokenKind.WORD and token.value == "include":
            yield from _process_include(cursor, token, state)
            continue
        if token.kind == TokenKind.WORD and token.value == "synonym":
            yield _parse_synonym(cursor, token, state)
            continue
        raise CompileError(
            f"line {token.line}: expected ':', 'variable', or 'create' at top level, "
            f"got {token.value!r}"
        )


def _parse_synonym(cursor: "_PeekableTokens", keyword: Token, state: _ProgramState) -> ColonDef:
    new_name = _read_synonym_name(cursor, keyword)
    _check_name_available(new_name, keyword, state)
    target_cell = _read_synonym_target(cursor, keyword, state)
    source_text = state.slice_source(keyword, cursor.last_consumed())
    state.dictionary.register(
        new_name, kind="colon", source=keyword.source, line=keyword.line,
        source_text=source_text,
    )
    return ColonDef(name=new_name, body=(target_cell,), source_text=source_text)


def _read_synonym_name(cursor: "_PeekableTokens", keyword: Token) -> str:
    name_token = cursor.next() if not cursor.eof() else None
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(
            f"line {keyword.line}: 'synonym' must be followed by a new name"
        )
    return name_token.value


def _read_synonym_target(
    cursor: "_PeekableTokens", keyword: Token, state: _ProgramState,
) -> "PrimRef | ColonRef":
    target_token = cursor.next() if not cursor.eof() else None
    if target_token is None or target_token.kind != TokenKind.WORD:
        raise CompileError(
            f"line {keyword.line}: 'synonym' must be followed by 'new-name target-name'"
        )
    target = target_token.value
    if is_primitive(target):
        return PrimRef(target)
    if target in state.dictionary:
        return ColonRef(target)
    raise CompileError(
        f"line {keyword.line}: 'synonym' target {target!r} is not defined"
    )


def _next_is_constant(cursor: "_PeekableTokens") -> bool:
    nxt = cursor.peek_at(0)
    return nxt is not None and nxt.kind == TokenKind.WORD and nxt.value == "constant"


def _parse_constant(
    cursor: "_PeekableTokens", value_token: Token, keyword: Token, state: _ProgramState,
) -> ColonDef:
    name = _read_definition_name(cursor, keyword, "constant")
    _check_name_available(name, keyword, state)
    source_text = state.slice_source(value_token, cursor.last_consumed())
    state.dictionary.register(
        name, kind="constant", source=keyword.source, line=keyword.line,
        source_text=source_text,
    )
    return ColonDef(name=name, body=(Literal(value_token.value),), source_text=source_text)


def _parse_variable(cursor: "_PeekableTokens", keyword: Token, state: _ProgramState) -> ColonDef:
    name = _read_definition_name(cursor, keyword, "variable")
    _check_name_available(name, keyword, state)
    offset = state.claim_address(CELL_BYTES)
    source_text = state.slice_source(keyword, cursor.last_consumed())
    state.dictionary.register(
        name, kind="variable", source=keyword.source, line=keyword.line,
        source_text=source_text,
    )
    return ColonDef(name=name, body=(Addr(offset),), source_text=source_text)


def _parse_create(cursor: "_PeekableTokens", keyword: Token, state: _ProgramState) -> ColonDef:
    name = _read_definition_name(cursor, keyword, "create")
    _check_name_available(name, keyword, state)
    offset = state.bump
    _consume_optional_allot(cursor, state)
    source_text = state.slice_source(keyword, cursor.last_consumed())
    state.dictionary.register(
        name, kind="create", source=keyword.source, line=keyword.line,
        source_text=source_text,
    )
    return ColonDef(name=name, body=(Addr(offset),), source_text=source_text)


def _consume_optional_allot(cursor: "_PeekableTokens", state: _ProgramState) -> None:
    while True:
        size_token = cursor.peek_at(0)
        allot_token = cursor.peek_at(1)
        if size_token is None or allot_token is None:
            return
        if not (allot_token.kind == TokenKind.WORD and allot_token.value == "allot"):
            return
        if size_token.kind != TokenKind.NUMBER or size_token.value < 0:
            raise CompileError(
                f"line {allot_token.line}: 'allot' size must be a positive integer literal, "
                f"got {size_token.value!r}"
            )
        cursor.next()
        cursor.next()
        state.bump += size_token.value


def _read_definition_name(cursor: "_PeekableTokens", keyword: Token, kind: str) -> str:
    name_token = cursor.next() if not cursor.eof() else None
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(
            f"line {keyword.line}: '{kind}' must be followed by a name"
        )
    return name_token.value


def _check_name_available(name: str, keyword: Token, state: _ProgramState) -> None:
    if name in _CONTROL_HANDLERS:
        raise CompileError(
            f"line {keyword.line}: cannot define {name!r} — it is a control-flow keyword"
        )
    if is_primitive(name):
        raise CompileError(
            f"line {keyword.line}: cannot define {name!r} — it is a built-in primitive"
        )
    previous = state.dictionary.get(name)
    if previous is not None:
        raise CompileError(
            f"line {keyword.line}: {name!r} is already defined "
            f"(first defined at {previous.source}:{previous.line})"
        )


def _parse_colon(cursor: "_PeekableTokens", colon_token: Token, state: _ProgramState) -> ColonDef:
    name_token = cursor.next() if not cursor.eof() else None
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(f"line {colon_token.line}: ':' must be followed by a word name")
    _check_name_available(name_token.value, colon_token, state)
    body_state = _BodyState(labels=state.labels, current_name=name_token.value)
    body = _parse_body(cursor, name_token, body_state, state)
    source_text = state.slice_source(colon_token, cursor.last_consumed())
    state.dictionary.register(
        name_token.value, kind="colon", source=colon_token.source, line=colon_token.line,
        source_text=source_text,
    )
    return ColonDef(name=name_token.value, body=body, source_text=source_text)


def _parse_body(
    cursor: "_PeekableTokens",
    name_token: Token,
    state: _BodyState,
    program: _ProgramState,
) -> tuple[Cell, ...]:
    while not cursor.eof():
        token = cursor.next()
        if token.kind == TokenKind.SEMI:
            if state.cf_stack:
                raise CompileError(
                    f"line {token.line}: ';' inside ':{name_token.value}' "
                    "with unclosed control flow"
                )
            if state.r_depth != 0:
                raise CompileError(
                    f"line {token.line}: ':{name_token.value}' ends with "
                    f"unbalanced return stack (depth={state.r_depth}); "
                    "every >r must be matched by an r> before ';'"
                )
            return tuple(state.cells)
        if token.kind == TokenKind.WORD and token.value == ":noname":
            _consume_noname(cursor, token, state, program)
            continue
        _consume_token(token, state, name_token)
    raise CompileError(
        f"line {name_token.line}: ':{name_token.value}' is missing closing ';'"
    )


def _consume_token(token: Token, state: _BodyState, name_token: Token) -> None:
    if token.kind == TokenKind.WORD and token.value == "include":
        raise CompileError(
            f"line {token.line}: 'include' must appear at top level, "
            f"not inside ':{name_token.value}'"
        )
    if token.kind == TokenKind.WORD and token.value == "synonym":
        raise CompileError(
            f"line {token.line}: 'synonym' must appear at top level, "
            f"not inside ':{name_token.value}'"
        )
    if token.kind == TokenKind.WORD and token.value in _CONTROL_HANDLERS:
        _CONTROL_HANDLERS[token.value](state, token)
        return
    cell = _to_cell(token)
    if isinstance(cell, PrimRef) and cell.name in _LOOP_INDEX_PRIMITIVES:
        _require_loop_depth(state, token, cell.name, 1)
    state.cells.append(cell)
    _track_return_stack(cell, token, state, name_token)


def _consume_noname(
    cursor: "_PeekableTokens",
    keyword: Token,
    outer: _BodyState,
    program: _ProgramState,
) -> None:
    name = program.fresh_noname_name()
    synthetic_token = Token(
        kind=TokenKind.WORD,
        value=name,
        line=keyword.line,
        col=keyword.col,
        source=keyword.source,
        raw=name,
    )
    body_state = _BodyState(labels=program.labels, current_name=name)
    body = _parse_body(cursor, synthetic_token, body_state, program)
    program.synthetic_defs.append(ColonDef(name=name, body=body))
    outer.cells.append(WordAddr(name))


def _process_include(
    cursor: "_PeekableTokens",
    keyword: Token,
    state: _ProgramState,
) -> Iterator[ColonDef]:
    if cursor.eof():
        raise CompileError(
            f"line {keyword.line}: 'include' must be followed by a filename"
        )
    name_token = cursor.next()
    if name_token.kind != TokenKind.WORD:
        raise CompileError(
            f"line {keyword.line}: 'include' must be followed by a filename, "
            f"got {name_token.value!r}"
        )
    try:
        path = state.resolver.resolve(name_token.value, state.current_source_path)
    except IncludeNotFound as exc:
        raise CompileError(f"line {keyword.line}: {exc}") from None
    if state.resolver.has_seen(path):
        return
    state.resolver.mark_seen(path)
    text = path.read_text()
    state.source_texts[str(path)] = text
    sub_tokens = tokenize(text, source=str(path))
    sub_cursor = _PeekableTokens(sub_tokens)
    previous_path = state.current_source_path
    state.current_source_path = path
    try:
        yield from _parse_top_level(sub_cursor, state)
    finally:
        state.current_source_path = previous_path


def _track_return_stack(cell: Cell, token: Token, state: _BodyState, name_token: Token) -> None:
    if not isinstance(cell, PrimRef):
        return
    if cell.name == ">r":
        state.r_depth += 1
        return
    if cell.name == "r>":
        if state.r_depth <= 0:
            raise CompileError(
                f"line {token.line}: 'r>' in ':{name_token.value}' "
                f"with empty return stack — no matching '>r' precedes it"
            )
        state.r_depth -= 1
        return
    if cell.name == "r@":
        if state.r_depth <= 0:
            raise CompileError(
                f"line {token.line}: 'r@' in ':{name_token.value}' "
                f"with empty return stack — no matching '>r' precedes it"
            )


def _to_cell(token: Token) -> Cell:
    if token.kind == TokenKind.NUMBER:
        return Literal(token.value)
    if token.kind == TokenKind.WORD:
        return _resolve_word(token.value)
    if token.kind == TokenKind.STRING:
        return StringLit(token.value)
    raise CompileError(f"line {token.line}: unexpected {token.value!r} inside colon body")


def _resolve_word(name: str) -> Cell:
    if is_primitive(name):
        return PrimRef(name)
    return ColonRef(name)


def _open_if(state: _BodyState, token: Token) -> None:
    label = state.labels.fresh()
    state.cells.append(Branch(target=label, conditional=True))
    state.cf_stack.push("orig", label)


def _switch_to_else(state: _BodyState, token: Token) -> None:
    if_label = _pop_orig(state, token, "else", "if")
    skip = state.labels.fresh()
    state.cells.append(Branch(target=skip, conditional=False))
    state.cells.append(Label(if_label))
    state.cf_stack.push("orig", skip)


def _close_then(state: _BodyState, token: Token) -> None:
    label = _pop_orig(state, token, "then", "if/else")
    state.cells.append(Label(label))


def _open_begin(state: _BodyState, token: Token) -> None:
    label = state.labels.fresh()
    state.cells.append(Label(label))
    state.cf_stack.push("dest", label)


def _close_until(state: _BodyState, token: Token) -> None:
    label = _pop_dest(state, token, "until", "begin")
    state.cells.append(Branch(target=label, conditional=True))


def _close_again(state: _BodyState, token: Token) -> None:
    label = _pop_dest(state, token, "again", "begin")
    state.cells.append(Branch(target=label, conditional=False))


def _open_while(state: _BodyState, token: Token) -> None:
    if not state.cf_stack or state.cf_stack.peek()[0] != "dest":
        raise CompileError(f"line {token.line}: 'while' without matching 'begin'")
    skip = state.labels.fresh()
    state.cells.append(Branch(target=skip, conditional=True))
    state.cf_stack.push("orig", skip)


def _close_repeat(state: _BodyState, token: Token) -> None:
    while_orig = _pop_orig(state, token, "repeat", "while")
    begin_dest = _pop_dest(state, token, "repeat", "begin")
    state.cells.append(Branch(target=begin_dest, conditional=False))
    state.cells.append(Label(while_orig))


def _open_do(state: _BodyState, token: Token) -> None:
    state.cells.append(PrimRef("(do)"))
    back = state.labels.fresh()
    exit_label = state.labels.fresh()
    state.cells.append(Label(back))
    state.cf_stack.push("do", _DoFrame(
        back_label=back, exit_label=exit_label, saved_r_depth=state.r_depth,
    ))


def _close_loop(state: _BodyState, token: Token) -> None:
    _close_loop_with(state, token, "loop", "(loop)")


def _close_plus_loop(state: _BodyState, token: Token) -> None:
    _close_loop_with(state, token, "+loop", "(+loop)")


def _close_loop_with(state: _BodyState, token: Token, current: str, test_prim: str) -> None:
    frame = _pop_do_frame(state, token, current)
    _require_balanced_return_stack(state, token, frame, current)
    state.cells.append(PrimRef(test_prim))
    state.cells.append(Branch(target=frame.back_label, conditional=True))
    state.cells.append(Label(frame.exit_label))
    state.cells.append(PrimRef("unloop"))


def _emit_leave(state: _BodyState, token: Token) -> None:
    found = state.cf_stack.find_innermost("do")
    if found is None:
        raise CompileError(
            f"line {token.line}: 'leave' outside any 'do' loop"
        )
    _, frame = found
    _require_balanced_return_stack(state, token, frame, "leave")
    state.cells.append(Branch(target=frame.exit_label, conditional=False))


def _emit_recurse(state: _BodyState, token: Token) -> None:
    state.cells.append(ColonRef(state.current_name))


def _pop_do_frame(state: _BodyState, token: Token, current: str) -> _DoFrame:
    try:
        frame = state.cf_stack.pop("do")
    except ControlStackError:
        raise CompileError(
            f"line {token.line}: {current!r} without matching 'do'"
        ) from None
    return frame


def _require_balanced_return_stack(
    state: _BodyState, token: Token, frame: _DoFrame, current: str,
) -> None:
    if state.r_depth != frame.saved_r_depth:
        raise CompileError(
            f"line {token.line}: {current!r} with unbalanced return stack "
            f"(was {frame.saved_r_depth} at 'do', is {state.r_depth} now); "
            "every >r inside the loop body must be matched by an r> before this point"
        )


def _require_loop_depth(state: _BodyState, token: Token, name: str, depth: int) -> None:
    count = sum(1 for tag, _ in state.cf_stack if tag == "do")
    if count < depth:
        raise CompileError(
            f"line {token.line}: {name!r} requires being inside at least {depth} "
            f"nested 'do' loop(s); currently inside {count}"
        )


def _pop_orig(state: _BodyState, token: Token, current: str, expected: str) -> int:
    return _pop_tagged(state, token, "orig", current, expected)


def _pop_dest(state: _BodyState, token: Token, current: str, expected: str) -> int:
    return _pop_tagged(state, token, "dest", current, expected)


def _pop_tagged(state: _BodyState, token: Token, tag: str, current: str, expected: str) -> int:
    try:
        return state.cf_stack.pop(tag)
    except ControlStackError:
        raise CompileError(
            f"line {token.line}: {current!r} without matching {expected!r}"
        ) from None


_CONTROL_HANDLERS = {
    "if":     _open_if,
    "else":   _switch_to_else,
    "then":   _close_then,
    "begin":  _open_begin,
    "until":  _close_until,
    "again":  _close_again,
    "while":  _open_while,
    "repeat": _close_repeat,
    "do":     _open_do,
    "loop":   _close_loop,
    "+loop":  _close_plus_loop,
    "leave":  _emit_leave,
    "recurse": _emit_recurse,
}


_LOOP_INDEX_PRIMITIVES = {"i", "j"}


@dataclass
class _PeekableTokens:
    tokens: list[Token]
    pos: int = 0

    def eof(self) -> bool:
        return self.pos >= len(self.tokens)

    def next(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def peek_at(self, offset: int) -> Token | None:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return None
        return self.tokens[idx]

    def last_consumed(self) -> Token:
        return self.tokens[self.pos - 1]


def program_user_memory_size(
    source: str,
    *,
    source_path: "Path | None" = None,
    include_dirs: "list[Path] | None" = None,
) -> int:
    cursor = _PeekableTokens(
        tokenize(source, source=str(source_path) if source_path else "<input>")
    )
    state = _ProgramState(
        resolver=IncludeResolver(include_dirs=include_dirs),
        current_source_path=source_path,
    )
    if source_path is not None:
        state.resolver.mark_seen(Path(source_path).resolve())
    list(_parse_top_level(cursor, state))
    return state.bump
