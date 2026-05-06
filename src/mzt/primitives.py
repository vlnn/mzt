from dataclasses import dataclass


@dataclass(frozen=True)
class Primitive:
    name: str
    label: str
    body: str
    inline: bool = False


def _binary_op(op: str) -> str:
    return (
        "    ldr     x0, [x19], #8\n"
        "    ldr     x1, [x19], #8\n"
        f"    {op}     x0, x1, x0\n"
        "    str     x0, [x19, #-8]!\n"
    )


def _comparison(cond: str) -> str:
    return (
        "    ldr     x0, [x19], #8\n"
        "    ldr     x1, [x19], #8\n"
        "    cmp     x1, x0\n"
        f"    csetm   x0, {cond}\n"
        "    str     x0, [x19, #-8]!\n"
    )


def _unary_in_place(op: str) -> str:
    return (
        "    ldr     x0, [x19]\n"
        f"    {op}     x0, x0\n"
        "    str     x0, [x19]\n"
    )


_DUP = (
    "    ldr     x0, [x19]\n"
    "    str     x0, [x19, #-8]!\n"
)


_DROP = "    add     x19, x19, #8\n"


_SWAP = (
    "    ldp     x0, x1, [x19]\n"
    "    stp     x1, x0, [x19]\n"
)


_OVER = (
    "    ldr     x0, [x19, #8]\n"
    "    str     x0, [x19, #-8]!\n"
)


_NIP = (
    "    ldr     x0, [x19]\n"
    "    add     x19, x19, #8\n"
    "    str     x0, [x19]\n"
)


_ROT = (
    "    ldp     x0, x1, [x19]\n"
    "    ldr     x2, [x19, #16]\n"
    "    str     x2, [x19]\n"
    "    stp     x0, x1, [x19, #8]\n"
)


_DIVMOD = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x19], #8\n"
    "    sdiv    x2, x1, x0\n"
    "    msub    x3, x2, x0, x1\n"
    "    str     x3, [x19, #-8]!\n"
    "    str     x2, [x19, #-8]!\n"
)


_ZERO_EQ = (
    "    ldr     x0, [x19]\n"
    "    cmp     x0, #0\n"
    "    csetm   x0, eq\n"
    "    str     x0, [x19]\n"
)


_ABS = (
    "    ldr     x0, [x19]\n"
    "    cmp     x0, #0\n"
    "    cneg    x0, x0, lt\n"
    "    str     x0, [x19]\n"
)


_DOT = (
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    ldr     x9, [x19], #8\n"
    "    sub     sp, sp, #16\n"
    "    str     x9, [sp]\n"
    "    adrp    x0, Lfmt_dot@PAGE\n"
    "    add     x0, x0, Lfmt_dot@PAGEOFF\n"
    "    bl      _printf\n"
    "    add     sp, sp, #16\n"
    "    ldp     x29, x30, [sp], #16\n"
)


_EMIT = (
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    sub     sp, sp, #16\n"
    "    ldr     x0, [x19], #8\n"
    "    strb    w0, [sp]\n"
    "    mov     x0, #1\n"
    "    mov     x1, sp\n"
    "    mov     x2, #1\n"
    "    bl      _write\n"
    "    add     sp, sp, #16\n"
    "    ldp     x29, x30, [sp], #16\n"
)


_CR = (
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    sub     sp, sp, #16\n"
    "    mov     w0, #10\n"
    "    strb    w0, [sp]\n"
    "    mov     x0, #1\n"
    "    mov     x1, sp\n"
    "    mov     x2, #1\n"
    "    bl      _write\n"
    "    add     sp, sp, #16\n"
    "    ldp     x29, x30, [sp], #16\n"
)


_PRIMITIVES: dict[str, Primitive] = {
    p.name: p for p in [
        Primitive("zero",   "_zero",   "    str     xzr, [x19, #-8]!\n", inline=True),
        Primitive("dup",    "_dup",    _DUP),
        Primitive("drop",   "_drop",   _DROP),
        Primitive("swap",   "_swap",   _SWAP),
        Primitive("over",   "_over",   _OVER),
        Primitive("nip",    "_nip",    _NIP),
        Primitive("rot",    "_rot",    _ROT),
        Primitive("+",      "_plus",   _binary_op("add")),
        Primitive("-",      "_minus",  _binary_op("sub")),
        Primitive("*",      "_star",   _binary_op("mul")),
        Primitive("/mod",   "_divmod", _DIVMOD),
        Primitive("=",      "_eq",     _comparison("eq")),
        Primitive("<",      "_lt",     _comparison("lt")),
        Primitive(">",      "_gt",     _comparison("gt")),
        Primitive("0=",     "_zeq",    _ZERO_EQ),
        Primitive("and",    "_and",    _binary_op("and")),
        Primitive("or",     "_or",     _binary_op("orr")),
        Primitive("xor",    "_xor",    _binary_op("eor")),
        Primitive("invert", "_invert", _unary_in_place("mvn")),
        Primitive("negate", "_negate", _unary_in_place("neg")),
        Primitive("abs",    "_abs",    _ABS),
        Primitive(".",      "_dot",    _DOT),
        Primitive("emit",   "_emit",   _EMIT),
        Primitive("cr",     "_cr",     _CR),
    ]
}


def is_primitive(name: str) -> bool:
    return name in _PRIMITIVES


def primitive(name: str) -> Primitive:
    return _PRIMITIVES[name]


def all_primitives() -> list[Primitive]:
    return list(_PRIMITIVES.values())
