from dataclasses import dataclass


@dataclass(frozen=True)
class Primitive:
    name: str
    label: str
    body: str
    inline: bool = False
    jit_only: bool = False


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


def _unary_inc(op: str) -> str:
    return (
        "    ldr     x0, [x19]\n"
        f"    {op}     x0, x0, #1\n"
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


_FETCH = (
    "    ldr     x0, [x19]\n"
    "    ldr     x0, [x0]\n"
    "    str     x0, [x19]\n"
)


_STORE = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x19], #8\n"
    "    str     x1, [x0]\n"
)


_CFETCH = (
    "    ldr     x0, [x19]\n"
    "    ldrb    w0, [x0]\n"
    "    str     x0, [x19]\n"
)


_CSTORE = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x19], #8\n"
    "    strb    w1, [x0]\n"
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


_TO_R = (
    "    ldr     x0, [x19], #8\n"
    "    str     x0, [x20, #-8]!\n"
)


_R_FROM = (
    "    ldr     x0, [x20], #8\n"
    "    str     x0, [x19, #-8]!\n"
)


_R_FETCH = (
    "    ldr     x0, [x20]\n"
    "    str     x0, [x19, #-8]!\n"
)


_DO_INIT = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x19], #8\n"
    "    str     x1, [x20, #-8]!\n"
    "    str     x0, [x20, #-8]!\n"
)


_LOOP_TEST = (
    "    ldr     x0, [x20]\n"
    "    add     x0, x0, #1\n"
    "    str     x0, [x20]\n"
    "    ldr     x1, [x20, #8]\n"
    "    cmp     x0, x1\n"
    "    csetm   x0, eq\n"
    "    str     x0, [x19, #-8]!\n"
)


_PLUS_LOOP_TEST = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x20]\n"
    "    add     x3, x1, x0\n"
    "    str     x3, [x20]\n"
    "    ldr     x2, [x20, #8]\n"
    "    cmp     x1, x2\n"
    "    csetm   x4, lt\n"
    "    cmp     x3, x2\n"
    "    csetm   x5, lt\n"
    "    eor     x6, x4, x5\n"
    "    cmp     x6, #0\n"
    "    csetm   x0, ne\n"
    "    str     x0, [x19, #-8]!\n"
)


_UNLOOP = "    add     x20, x20, #16\n"


_LOOP_I = (
    "    ldr     x0, [x20]\n"
    "    str     x0, [x19, #-8]!\n"
)


_LOOP_J = (
    "    ldr     x0, [x20, #16]\n"
    "    str     x0, [x19, #-8]!\n"
)


_EXECUTE = (
    "    ldr     x9, [x19], #8\n"
    "    br      x9\n"
)


_HALT = (
    "    ldr     x0, [x19], #8\n"
    "    bl      _exit\n"
)


_KEY = (
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    sub     sp, sp, #16\n"
    "    mov     x0, #0\n"
    "    mov     x1, sp\n"
    "    mov     x2, #1\n"
    "    bl      _read\n"
    "    ldrb    w1, [sp]\n"
    "    mov     x2, #-1\n"
    "    cmp     x0, #1\n"
    "    csel    x0, x1, x2, eq\n"
    "    str     x0, [x19, #-8]!\n"
    "    add     sp, sp, #16\n"
    "    ldp     x29, x30, [sp], #16\n"
)


_DUMP_STACKS = (
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    stp     x21, x22, [sp, #-16]!\n"
    "    adrp    x0, Lfmt_dump_dstack@PAGE\n"
    "    add     x0, x0, Lfmt_dump_dstack@PAGEOFF\n"
    "    adrp    x21, Ldstack_base@PAGE\n"
    "    add     x21, x21, Ldstack_base@PAGEOFF\n"
    f"    add     x21, x21, #{8192}\n"
    "    sub     x1, x21, x19\n"
    "    asr     x1, x1, #3\n"
    "    sub     sp, sp, #16\n"
    "    str     x1, [sp]\n"
    "    bl      _printf\n"
    "    add     sp, sp, #16\n"
    "    sub     x22, x21, #8\n"
    "Ldump_d_loop:\n"
    "    cmp     x22, x19\n"
    "    b.lt    Ldump_d_done\n"
    "    ldr     x1, [x22]\n"
    "    sub     sp, sp, #16\n"
    "    str     x1, [sp]\n"
    "    adrp    x0, Lfmt_dump_cell@PAGE\n"
    "    add     x0, x0, Lfmt_dump_cell@PAGEOFF\n"
    "    bl      _printf\n"
    "    add     sp, sp, #16\n"
    "    sub     x22, x22, #8\n"
    "    b       Ldump_d_loop\n"
    "Ldump_d_done:\n"
    "    adrp    x0, Lfmt_dump_rstack@PAGE\n"
    "    add     x0, x0, Lfmt_dump_rstack@PAGEOFF\n"
    "    adrp    x21, Lrstack_base@PAGE\n"
    "    add     x21, x21, Lrstack_base@PAGEOFF\n"
    f"    add     x21, x21, #{4096}\n"
    "    sub     x1, x21, x20\n"
    "    asr     x1, x1, #3\n"
    "    sub     sp, sp, #16\n"
    "    str     x1, [sp]\n"
    "    bl      _printf\n"
    "    add     sp, sp, #16\n"
    "    sub     x22, x21, #8\n"
    "Ldump_r_loop:\n"
    "    cmp     x22, x20\n"
    "    b.lt    Ldump_r_done\n"
    "    ldr     x1, [x22]\n"
    "    sub     sp, sp, #16\n"
    "    str     x1, [sp]\n"
    "    adrp    x0, Lfmt_dump_cell@PAGE\n"
    "    add     x0, x0, Lfmt_dump_cell@PAGEOFF\n"
    "    bl      _printf\n"
    "    add     sp, sp, #16\n"
    "    sub     x22, x22, #8\n"
    "    b       Ldump_r_loop\n"
    "Ldump_r_done:\n"
    "    ldp     x21, x22, [sp], #16\n"
    "    ldp     x29, x30, [sp], #16\n"
)


_DISPATCH_MAIN = (
    "    ldr     x0, [x19], #8\n"
    "    stp     x29, x30, [sp, #-16]!\n"
    "    mov     x29, sp\n"
    "    bl      _mzt_dispatch_main\n"
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
        Primitive("1+",     "_one_plus",  _unary_inc("add")),
        Primitive("1-",     "_one_minus", _unary_inc("sub")),
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
        Primitive("@",      "_fetch",  _FETCH),
        Primitive("!",      "_store",  _STORE),
        Primitive("c@",     "_cfetch", _CFETCH),
        Primitive("c!",     "_cstore", _CSTORE),
        Primitive(">r",     "_to_r",    _TO_R),
        Primitive("r>",     "_r_from",  _R_FROM),
        Primitive("r@",     "_r_fetch", _R_FETCH),
        Primitive("(do)",    "_do_init",        _DO_INIT),
        Primitive("(loop)",  "_loop_test",      _LOOP_TEST),
        Primitive("(+loop)", "_plus_loop_test", _PLUS_LOOP_TEST),
        Primitive("unloop",  "_unloop",         _UNLOOP),
        Primitive("i",       "_loop_i",         _LOOP_I),
        Primitive("j",       "_loop_j",         _LOOP_J),
        Primitive("execute", "_execute",        _EXECUTE),
        Primitive("halt",    "_halt",           _HALT),
        Primitive("key",     "_key",            _KEY),
        Primitive("dispatch-main", "_dispatch_main", _DISPATCH_MAIN, jit_only=True),
        Primitive("__dump-stacks", "_dump_stacks", _DUMP_STACKS),
    ]
}


def is_primitive(name: str) -> bool:
    return name in _PRIMITIVES


def primitive(name: str) -> Primitive:
    return _PRIMITIVES[name]


def all_primitives() -> list[Primitive]:
    return list(_PRIMITIVES.values())
