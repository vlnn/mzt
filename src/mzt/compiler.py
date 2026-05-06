from collections.abc import Iterator
from dataclasses import dataclass, field

from mzt.ir import Addr, Branch, Cell, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit
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


@dataclass
class _BodyState:
    cells: list[Cell] = field(default_factory=list)
    cf_stack: list[tuple[str, int]] = field(default_factory=list)
    labels: _LabelGen = field(default_factory=_LabelGen)


@dataclass
class _ProgramState:
    bump: int = 0
    defined_names: set[str] = field(default_factory=set)
    labels: _LabelGen = field(default_factory=_LabelGen)

    def claim_address(self, size: int) -> int:
        offset = self.bump
        self.bump += size
        return offset


def compile_source(source: str) -> list[ColonDef]:
    return compile_tokens(tokenize(source))


def compile_tokens(tokens: list[Token]) -> list[ColonDef]:
    cursor = _PeekableTokens(tokens)
    state = _ProgramState()
    return list(_parse_top_level(cursor, state))


def _parse_top_level(cursor: "_PeekableTokens", state: _ProgramState) -> Iterator[ColonDef]:
    while not cursor.eof():
        token = cursor.next()
        if token.kind == TokenKind.COLON:
            yield _parse_colon(cursor, token.line, state)
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
        raise CompileError(
            f"line {token.line}: expected ':', 'variable', or 'create' at top level, "
            f"got {token.value!r}"
        )


def _parse_variable(cursor: "_PeekableTokens", keyword: Token, state: _ProgramState) -> ColonDef:
    name = _read_definition_name(cursor, keyword, "variable")
    _check_name_available(name, keyword.line, state)
    offset = state.claim_address(CELL_BYTES)
    state.defined_names.add(name)
    return ColonDef(name=name, body=(Addr(offset),))


def _parse_create(cursor: "_PeekableTokens", keyword: Token, state: _ProgramState) -> ColonDef:
    name = _read_definition_name(cursor, keyword, "create")
    _check_name_available(name, keyword.line, state)
    offset = state.bump
    _consume_optional_allot(cursor, state)
    state.defined_names.add(name)
    return ColonDef(name=name, body=(Addr(offset),))


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


def _check_name_available(name: str, line: int, state: _ProgramState) -> None:
    if name in _CONTROL_HANDLERS:
        raise CompileError(
            f"line {line}: cannot define {name!r} — it is a control-flow keyword"
        )
    if is_primitive(name):
        raise CompileError(
            f"line {line}: cannot define {name!r} — it is a built-in primitive"
        )
    if name in state.defined_names:
        raise CompileError(
            f"line {line}: {name!r} is already defined"
        )


def _parse_colon(cursor: "_PeekableTokens", colon_line: int, state: _ProgramState) -> ColonDef:
    name_token = cursor.next() if not cursor.eof() else None
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(f"line {colon_line}: ':' must be followed by a word name")
    if name_token.value in _CONTROL_HANDLERS:
        raise CompileError(
            f"line {colon_line}: cannot define a colon word named {name_token.value!r} "
            "(it is a control-flow keyword)"
        )
    if name_token.value in state.defined_names:
        raise CompileError(f"line {colon_line}: {name_token.value!r} is already defined")
    body_state = _BodyState(labels=state.labels)
    body = _parse_body(cursor, name_token, body_state)
    state.defined_names.add(name_token.value)
    return ColonDef(name=name_token.value, body=body)


def _parse_body(cursor: "_PeekableTokens", name_token: Token, state: _BodyState) -> tuple[Cell, ...]:
    while not cursor.eof():
        token = cursor.next()
        if token.kind == TokenKind.SEMI:
            if state.cf_stack:
                raise CompileError(
                    f"line {token.line}: ';' inside ':{name_token.value}' "
                    "with unclosed control flow"
                )
            return tuple(state.cells)
        _consume_token(token, state)
    raise CompileError(
        f"line {name_token.line}: ':{name_token.value}' is missing closing ';'"
    )


def _consume_token(token: Token, state: _BodyState) -> None:
    if token.kind == TokenKind.WORD and token.value in _CONTROL_HANDLERS:
        _CONTROL_HANDLERS[token.value](state, token)
        return
    state.cells.append(_to_cell(token))


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
    state.cf_stack.append(("orig", label))


def _switch_to_else(state: _BodyState, token: Token) -> None:
    if_label = _pop_orig(state, token, "else", "if")
    skip = state.labels.fresh()
    state.cells.append(Branch(target=skip, conditional=False))
    state.cells.append(Label(if_label))
    state.cf_stack.append(("orig", skip))


def _close_then(state: _BodyState, token: Token) -> None:
    label = _pop_orig(state, token, "then", "if/else")
    state.cells.append(Label(label))


def _open_begin(state: _BodyState, token: Token) -> None:
    label = state.labels.fresh()
    state.cells.append(Label(label))
    state.cf_stack.append(("dest", label))


def _close_until(state: _BodyState, token: Token) -> None:
    label = _pop_dest(state, token, "until", "begin")
    state.cells.append(Branch(target=label, conditional=True))


def _close_again(state: _BodyState, token: Token) -> None:
    label = _pop_dest(state, token, "again", "begin")
    state.cells.append(Branch(target=label, conditional=False))


def _open_while(state: _BodyState, token: Token) -> None:
    if not state.cf_stack or state.cf_stack[-1][0] != "dest":
        raise CompileError(f"line {token.line}: 'while' without matching 'begin'")
    skip = state.labels.fresh()
    state.cells.append(Branch(target=skip, conditional=True))
    state.cf_stack.append(("orig", skip))


def _close_repeat(state: _BodyState, token: Token) -> None:
    while_orig = _pop_orig(state, token, "repeat", "while")
    begin_dest = _pop_dest(state, token, "repeat", "begin")
    state.cells.append(Branch(target=begin_dest, conditional=False))
    state.cells.append(Label(while_orig))


def _pop_orig(state: _BodyState, token: Token, current: str, expected: str) -> int:
    if not state.cf_stack or state.cf_stack[-1][0] != "orig":
        raise CompileError(f"line {token.line}: {current!r} without matching {expected!r}")
    return state.cf_stack.pop()[1]


def _pop_dest(state: _BodyState, token: Token, current: str, expected: str) -> int:
    if not state.cf_stack or state.cf_stack[-1][0] != "dest":
        raise CompileError(f"line {token.line}: {current!r} without matching {expected!r}")
    return state.cf_stack.pop()[1]


_CONTROL_HANDLERS = {
    "if":     _open_if,
    "else":   _switch_to_else,
    "then":   _close_then,
    "begin":  _open_begin,
    "until":  _close_until,
    "again":  _close_again,
    "while":  _open_while,
    "repeat": _close_repeat,
}


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


def program_user_memory_size(source: str) -> int:
    cursor = _PeekableTokens(tokenize(source))
    state = _ProgramState()
    list(_parse_top_level(cursor, state))
    return state.bump
