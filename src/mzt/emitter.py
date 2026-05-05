from mzt.ir import Cell, ColonDef, ColonRef, Literal, PrimRef
from mzt.primitives import primitive
from mzt.runtime import runtime_epilogue, runtime_preamble


def emit_program(defs: list[ColonDef]) -> str:
    parts = [runtime_preamble()]
    parts.extend(_emit_colon_def(d) for d in defs)
    parts.append(runtime_epilogue())
    return "".join(parts)


def _emit_colon_def(d: ColonDef) -> str:
    body = "".join(_emit_cell(c) for c in d.body)
    return (
        f"_word_{d.name}:\n"
        f"    stp     x29, x30, [sp, #-16]!\n"
        f"    mov     x29, sp\n"
        f"{body}"
        f"    ldp     x29, x30, [sp], #16\n"
        f"    ret\n\n"
    )


def _emit_cell(cell: Cell) -> str:
    if isinstance(cell, Literal):
        return _emit_literal(cell)
    if isinstance(cell, PrimRef):
        return f"    bl      {primitive(cell.name).label}\n"
    if isinstance(cell, ColonRef):
        return f"    bl      _word_{cell.name}\n"
    raise TypeError(f"unknown IR cell {cell!r}")


def _emit_literal(lit: Literal) -> str:
    return (
        f"    ldr     x0, ={lit.value}\n"
        f"    str     x0, [x19, #-8]!\n"
    )
