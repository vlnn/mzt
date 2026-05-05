from mzt.primitives import Primitive, all_primitives


DSTACK_BYTES = 8192


def runtime_preamble() -> str:
    return _entry_point() + "".join(_emit_primitive(p) for p in all_primitives())


def runtime_epilogue() -> str:
    return _rodata() + _bss()


def _entry_point() -> str:
    return f"""\
.section __TEXT,__text,regular,pure_instructions
.globl  _main
.p2align 2

_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x19, Ldstack_base@PAGE
    add     x19, x19, Ldstack_base@PAGEOFF
    add     x19, x19, #{DSTACK_BYTES}
    bl      _word_main
    mov     w0, #0
    ldp     x29, x30, [sp], #16
    ret

"""


def _emit_primitive(p: Primitive) -> str:
    return f"{p.label}:\n{p.body}    ret\n\n"


def _rodata() -> str:
    return (
        "\n.section __TEXT,__cstring,cstring_literals\n"
        "Lfmt_dot:\n"
        '    .asciz  "%lld\\n"\n'
    )


def _bss() -> str:
    return f"\n.zerofill __DATA,__bss,Ldstack_base,{DSTACK_BYTES},3\n"
