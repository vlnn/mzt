from dataclasses import dataclass, field

from mzt.ir import Addr, Branch, Cell, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit, WordAddr
from mzt.primitives import primitive
from mzt.runtime import runtime_epilogue, runtime_preamble


@dataclass
class _StringTable:
    entries: list[tuple[str, bytes]] = field(default_factory=list)

    def intern(self, content: str) -> tuple[str, int]:
        idx = len(self.entries)
        label = f"Lstr_{idx}"
        encoded = content.encode("utf-8")
        self.entries.append((label, encoded))
        return label, len(encoded)


def emit_program(defs: list[ColonDef], user_memory_bytes: int = 0) -> str:
    _check_label_collisions(defs)
    strings = _StringTable()
    parts = [runtime_preamble()]
    parts.extend(_emit_colon_def(d, strings) for d in defs)
    parts.append(runtime_epilogue(user_memory_bytes))
    if strings.entries:
        parts.append(_emit_string_table(strings))
    return "".join(parts)


def _check_label_collisions(defs: list[ColonDef]) -> None:
    label_to_names: dict[str, list[str]] = {}
    for d in defs:
        label_to_names.setdefault(_word_label(d.name), []).append(d.name)
    collisions = {label: names for label, names in label_to_names.items() if len(names) > 1}
    if collisions:
        report = "; ".join(
            f"{names!r} all sanitize to {label!r}"
            for label, names in collisions.items()
        )
        raise ValueError(
            f"colon-name sanitization collision (hyphens become underscores): {report}"
        )


def _emit_colon_def(d: ColonDef, strings: _StringTable) -> str:
    body = "".join(_emit_cell(c, strings) for c in d.body)
    return (
        f"{_word_label(d.name)}:\n"
        f"    stp     x29, x30, [sp, #-16]!\n"
        f"    mov     x29, sp\n"
        f"{body}"
        f"    ldp     x29, x30, [sp], #16\n"
        f"    ret\n\n"
    )


def _emit_cell(cell: Cell, strings: _StringTable) -> str:
    if isinstance(cell, Literal):
        return _emit_literal(cell)
    if isinstance(cell, PrimRef):
        prim = primitive(cell.name)
        if prim.inline:
            return prim.body
        return f"    bl      {prim.label}\n"
    if isinstance(cell, ColonRef):
        return f"    bl      {_word_label(cell.name)}\n"
    if isinstance(cell, Label):
        return f"L{cell.id}:\n"
    if isinstance(cell, Branch):
        return _emit_branch(cell)
    if isinstance(cell, StringLit):
        return _emit_string_lit(cell, strings)
    if isinstance(cell, Addr):
        return _emit_addr(cell)
    if isinstance(cell, WordAddr):
        return _emit_word_addr(cell)
    raise TypeError(f"unknown IR cell {cell!r}")


_LABEL_CHAR_REPLACEMENTS = {
    "-": "_",
    "?": "_q_",
    "/": "_slash_",
    "!": "_store_",
    "@": "_fetch_",
    "+": "_plus_",
    "*": "_star_",
    "<": "_lt_",
    ">": "_gt_",
    "=": "_eq_",
    ".": "_dot_",
    ",": "_comma_",
    "%": "_pct_",
    "&": "_amp_",
    "|": "_pipe_",
    "^": "_caret_",
    "~": "_tilde_",
    "#": "_hash_",
    "$": "_dollar_",
    ":": "_colon_",
    ";": "_semi_",
    "(": "_lparen_",
    ")": "_rparen_",
    "[": "_lbrack_",
    "]": "_rbrack_",
    "{": "_lbrace_",
    "}": "_rbrace_",
}


def _word_label(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append(_LABEL_CHAR_REPLACEMENTS.get(ch, "_"))
    return "_word_" + "".join(out)


def _emit_word_addr(word: WordAddr) -> str:
    label = _word_label(word.name)
    return (
        f"    adrp    x0, {label}@PAGE\n"
        f"    add     x0, x0, {label}@PAGEOFF\n"
        f"    str     x0, [x19, #-8]!\n"
    )


def _emit_addr(addr: Addr) -> str:
    base_load = (
        "    adrp    x0, Luser_mem@PAGE\n"
        "    add     x0, x0, Luser_mem@PAGEOFF\n"
    )
    if addr.offset == 0:
        return base_load + "    str     x0, [x19, #-8]!\n"
    return (
        base_load
        + f"    add     x0, x0, #{addr.offset}\n"
        + "    str     x0, [x19, #-8]!\n"
    )


def _emit_literal(lit: Literal) -> str:
    return (
        f"    ldr     x0, ={lit.value}\n"
        f"    str     x0, [x19, #-8]!\n"
    )


def _emit_branch(branch: Branch) -> str:
    if branch.conditional:
        return (
            f"    ldr     x0, [x19], #8\n"
            f"    cbz     x0, L{branch.target}\n"
        )
    return f"    b       L{branch.target}\n"


def _emit_string_lit(lit: StringLit, strings: _StringTable) -> str:
    label, length = strings.intern(lit.content)
    return (
        f"    adrp    x0, {label}@PAGE\n"
        f"    add     x0, x0, {label}@PAGEOFF\n"
        f"    mov     x1, #{length}\n"
        f"    bl      _print_str\n"
    )


def _emit_string_table(strings: _StringTable) -> str:
    parts = ["\n.section __TEXT,__cstring,cstring_literals\n"]
    for label, encoded in strings.entries:
        parts.append(f"{label}:\n    .asciz  \"{_escape(encoded)}\"\n")
    return "".join(parts)


def _escape(data: bytes) -> str:
    chunks = []
    for byte in data:
        if byte == ord("\\"):
            chunks.append("\\\\")
        elif byte == ord('"'):
            chunks.append('\\"')
        elif 32 <= byte < 127:
            chunks.append(chr(byte))
        else:
            chunks.append(f"\\{byte:03o}")
    return "".join(chunks)
