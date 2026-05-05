from dataclasses import dataclass


@dataclass(frozen=True)
class Primitive:
    name: str
    label: str
    body: str


_PLUS_BODY = (
    "    ldr     x0, [x19], #8\n"
    "    ldr     x1, [x19], #8\n"
    "    add     x0, x1, x0\n"
    "    str     x0, [x19, #-8]!\n"
)


_DOT_BODY = (
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


_PRIMITIVES: dict[str, Primitive] = {
    "+": Primitive(name="+", label="_plus", body=_PLUS_BODY),
    ".": Primitive(name=".", label="_dot", body=_DOT_BODY),
}


def is_primitive(name: str) -> bool:
    return name in _PRIMITIVES


def primitive(name: str) -> Primitive:
    return _PRIMITIVES[name]


def all_primitives() -> list[Primitive]:
    return list(_PRIMITIVES.values())
