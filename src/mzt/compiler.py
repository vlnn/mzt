from collections.abc import Iterator
from dataclasses import dataclass, field

from mzt.ir import Branch, Cell, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit
from mzt.primitives import is_primitive
from mzt.tokenizer import Token, TokenKind, tokenize


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


def compile_source(source: str) -> list[ColonDef]:
    return compile_tokens(tokenize(source))


def compile_tokens(tokens: list[Token]) -> list[ColonDef]:
    cursor = iter(tokens)
    labels = _LabelGen()
    return list(_parse_top_level(cursor, labels))


def _parse_top_level(cursor: Iterator[Token], labels: _LabelGen) -> Iterator[ColonDef]:
    for token in cursor:
        if token.kind != TokenKind.COLON:
            raise CompileError(
                f"line {token.line}: expected ':' at top level, got {token.value!r}"
            )
        yield _parse_colon(cursor, token.line, labels)


def _parse_colon(cursor: Iterator[Token], colon_line: int, labels: _LabelGen) -> ColonDef:
    name_token = next(cursor, None)
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(f"line {colon_line}: ':' must be followed by a word name")
    if name_token.value in _CONTROL_HANDLERS:
        raise CompileError(
            f"line {colon_line}: cannot define a colon word named {name_token.value!r} "
            "(it is a control-flow keyword)"
        )
    state = _BodyState(labels=labels)
    body = _parse_body(cursor, name_token, state)
    return ColonDef(name=name_token.value, body=body)


def _parse_body(cursor: Iterator[Token], name_token: Token, state: _BodyState) -> tuple[Cell, ...]:
    for token in cursor:
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
        raise CompileError(
            f"line {token.line}: 'while' without matching 'begin'"
        )
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
        raise CompileError(
            f"line {token.line}: {current!r} without matching {expected!r}"
        )
    return state.cf_stack.pop()[1]


def _pop_dest(state: _BodyState, token: Token, current: str, expected: str) -> int:
    if not state.cf_stack or state.cf_stack[-1][0] != "dest":
        raise CompileError(
            f"line {token.line}: {current!r} without matching {expected!r}"
        )
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
