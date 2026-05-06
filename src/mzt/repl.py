from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from mzt.compiler import CompileError
from mzt.session import Session, save_session, save_word
from mzt.tokenizer import Token, TokenKind, TokenizerError, tokenize


class ReplExit(Exception):
    pass


Executor = Callable[[Session, str], str]


def _noop_executor(session: Session, expression: str) -> str:
    return ""


@dataclass
class Repl:
    executor: Executor = _noop_executor
    include_dirs: list[Path] = field(default_factory=list)
    session: Session = field(init=False)

    def __post_init__(self) -> None:
        self.session = Session(include_dirs=list(self.include_dirs))


def run_line(repl: Repl, line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith(":") and _looks_like_meta(stripped):
        return _dispatch_meta(repl, stripped)
    return _run_program_line(repl, line)


def _looks_like_meta(stripped: str) -> bool:
    head = stripped.split(None, 1)[0]
    return len(head) > 1 and head[1:].replace("-", "").isalpha()


def _dispatch_meta(repl: Repl, line: str) -> str:
    parts = line.split()
    command, args = parts[0], parts[1:]
    handler = _META_COMMANDS.get(command)
    if handler is None:
        return f"unknown command {command!r}; try :help"
    try:
        return handler(repl, args)
    except (KeyError, ValueError) as e:
        return f"{command}: {e}"


def _meta_save(repl: Repl, args: list[str]) -> str:
    if len(args) == 1:
        save_session(repl.session, Path(args[0]))
        return f"wrote session to {args[0]}"
    if len(args) == 2:
        name, target = args
        save_word(repl.session, name, Path(target))
        return f"wrote {name} to {target}"
    return ":save expects either PATH (full session) or NAME PATH (single word)"


def _meta_words(repl: Repl, args: list[str]) -> str:
    names = sorted(repl.session.state.dictionary)
    return " ".join(names) if names else "(no words defined)"


def _meta_quit(repl: Repl, args: list[str]) -> str:
    raise ReplExit


def _meta_help(repl: Repl, args: list[str]) -> str:
    return (
        ":save PATH         save the whole session to a file\n"
        ":save NAME PATH    save a single word's source\n"
        ":words             list defined words\n"
        ":quit              exit the REPL"
    )


_META_COMMANDS = {
    ":save": _meta_save,
    ":words": _meta_words,
    ":quit": _meta_quit,
    ":exit": _meta_quit,
    ":help": _meta_help,
}


def _run_program_line(repl: Repl, line: str) -> str:
    try:
        defs_part, expression_part = _split_defs_and_expression(line)
    except (CompileError, TokenizerError) as e:
        return str(e)
    messages: list[str] = []
    if defs_part:
        message = _feed_definitions(repl, defs_part)
        if message:
            messages.append(message)
    if expression_part:
        message = _evaluate_expression(repl, expression_part)
        if message:
            messages.append(message)
    return "".join(messages)


def _feed_definitions(repl: Repl, defs_part: str) -> str:
    warnings_before = len(repl.session.state.warnings)
    try:
        repl.session.feed(defs_part)
    except (CompileError, TokenizerError) as e:
        return f"{e}\n"
    new_warnings = repl.session.state.warnings[warnings_before:]
    if new_warnings:
        return "".join(f"warning: {w}\n" for w in new_warnings)
    return ""


def _evaluate_expression(repl: Repl, expression: str) -> str:
    try:
        return repl.executor(repl.session, expression)
    except Exception as e:
        return f"error: {e}\n"


def _split_defs_and_expression(line: str) -> tuple[str, str]:
    tokens = tokenize(line, source="<repl-split>")
    if not tokens:
        return "", ""
    boundary = _find_definition_boundary(tokens, line)
    if boundary == len(tokens):
        return line, ""
    if boundary == 0:
        return "", line
    cut = tokens[boundary].start_offset
    defs_part = line[:cut].rstrip()
    expr_part = line[cut:]
    return defs_part, expr_part


def _find_definition_boundary(tokens: list[Token], source: str) -> int:
    """Return the index of the first token that's *not* part of a top-level
    definition. Walk the token stream, advance past each recognised def form,
    stop at the first token that doesn't fit. Raises CompileError if a def
    form starts but doesn't complete."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not _starts_definition(token, tokens, i):
            return i
        consumed = _consume_definition(tokens, i)
        if consumed is None:
            raise CompileError(_incomplete_message(token, tokens, i))
        i = consumed
    return i


def _incomplete_message(token: Token, tokens: list[Token], i: int) -> str:
    if token.kind == TokenKind.COLON:
        name = tokens[i + 1].raw if i + 1 < len(tokens) else "?"
        return f"line {token.line}: expected ';' to close ': {name}'"
    return f"line {token.line}: incomplete definition starting at {token.raw!r}"


def _starts_definition(token: Token, tokens: list[Token], i: int) -> bool:
    if token.kind == TokenKind.COLON:
        return True
    if token.kind == TokenKind.WORD and token.value in {
        "synonym", "variable", "create", "include",
    }:
        return True
    if token.kind == TokenKind.NUMBER and _next_word_is(tokens, i + 1, "constant"):
        return True
    return False


def _consume_definition(tokens: list[Token], i: int) -> int | None:
    token = tokens[i]
    if token.kind == TokenKind.COLON:
        return _consume_through_semi(tokens, i + 1)
    if token.kind == TokenKind.WORD and token.value == "synonym":
        return _consume_n(tokens, i + 1, 2)
    if token.kind == TokenKind.WORD and token.value == "variable":
        return _consume_n(tokens, i + 1, 1)
    if token.kind == TokenKind.WORD and token.value == "create":
        return _consume_create(tokens, i + 1)
    if token.kind == TokenKind.WORD and token.value == "include":
        return _consume_n(tokens, i + 1, 1)
    if token.kind == TokenKind.NUMBER and _next_word_is(tokens, i + 1, "constant"):
        return _consume_n(tokens, i + 2, 1)
    return None


def _consume_through_semi(tokens: list[Token], start: int) -> int | None:
    i = start
    while i < len(tokens):
        if tokens[i].kind == TokenKind.SEMI:
            return i + 1
        i += 1
    return None


def _consume_n(tokens: list[Token], start: int, count: int) -> int | None:
    end = start + count
    return end if end <= len(tokens) else None


def _consume_create(tokens: list[Token], start: int) -> int | None:
    if start >= len(tokens):
        return None
    i = start + 1  # past the name
    while (
        i + 1 < len(tokens)
        and tokens[i].kind == TokenKind.NUMBER
        and _next_word_is(tokens, i + 1, "allot")
    ):
        i += 2
    return i


def _next_word_is(tokens: list[Token], idx: int, word: str) -> bool:
    return (
        idx < len(tokens)
        and tokens[idx].kind == TokenKind.WORD
        and tokens[idx].value == word
    )
