from dataclasses import dataclass, field

from mzt.ir import Branch, Cell, ColonDef, ColonRef, Label, Literal, PrimRef, StringLit
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


def emit_program(defs: list[ColonDef]) -> str:
    strings = _StringTable()
    parts = [runtime_preamble()]
    parts.extend(_emit_colon_def(d, strings) for d in defs)
    parts.append(runtime_epilogue())
    if strings.entries:
        parts.append(_emit_string_table(strings))
    return "".join(parts)


def _emit_colon_def(d: ColonDef, strings: _StringTable) -> str:
    body = "".join(_emit_cell(c, strings) for c in d.body)
    return (
        f"_word_{d.name}:\n"
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
        return f"    bl      {primitive(cell.name).label}\n"
    if isinstance(cell, ColonRef):
        return f"    bl      _word_{cell.name}\n"
    if isinstance(cell, Label):
        return f"L{cell.id}:\n"
    if isinstance(cell, Branch):
        return _emit_branch(cell)
    if isinstance(cell, StringLit):
        return _emit_string_lit(cell, strings)
    raise TypeError(f"unknown IR cell {cell!r}")


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
