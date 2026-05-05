from collections.abc import Iterator

from mzt.ir import Cell, ColonDef, ColonRef, Literal, PrimRef
from mzt.primitives import is_primitive
from mzt.tokenizer import Token, TokenKind, tokenize


class CompileError(Exception):
    pass


def compile_source(source: str) -> list[ColonDef]:
    return compile_tokens(tokenize(source))


def compile_tokens(tokens: list[Token]) -> list[ColonDef]:
    cursor = iter(tokens)
    return list(_parse_top_level(cursor))


def _parse_top_level(cursor: Iterator[Token]) -> Iterator[ColonDef]:
    for token in cursor:
        if token.kind != TokenKind.COLON:
            raise CompileError(
                f"line {token.line}: expected ':' at top level, got {token.value!r}"
            )
        yield _parse_colon(cursor, token.line)


def _parse_colon(cursor: Iterator[Token], colon_line: int) -> ColonDef:
    name_token = next(cursor, None)
    if name_token is None or name_token.kind != TokenKind.WORD:
        raise CompileError(
            f"line {colon_line}: ':' must be followed by a word name"
        )
    body = tuple(_parse_body(cursor, name_token))
    return ColonDef(name=name_token.value, body=body)


def _parse_body(cursor: Iterator[Token], name_token: Token) -> Iterator[Cell]:
    for token in cursor:
        if token.kind == TokenKind.SEMI:
            return
        yield _to_cell(token)
    raise CompileError(
        f"line {name_token.line}: ':{name_token.value}' is missing closing ';'"
    )


def _to_cell(token: Token) -> Cell:
    if token.kind == TokenKind.NUMBER:
        return Literal(token.value)
    if token.kind == TokenKind.WORD:
        return _resolve_word(token.value)
    raise CompileError(
        f"line {token.line}: unexpected {token.value!r} inside colon body"
    )


def _resolve_word(name: str) -> Cell:
    if is_primitive(name):
        return PrimRef(name)
    return ColonRef(name)
