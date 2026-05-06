from mzt.primitives import Primitive, all_primitives


DSTACK_BYTES = 8192
USER_MEMORY_MIN_BYTES = 16


def runtime_preamble() -> str:
    return (
        _entry_point()
        + _print_str_helper()
        + "".join(_emit_primitive(p) for p in all_primitives() if not p.inline)
    )


def runtime_epilogue(user_memory_bytes: int = 0) -> str:
    return _rodata() + _bss(user_memory_bytes)


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


def _print_str_helper() -> str:
    return """\
_print_str:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    mov     x2, x1
    mov     x1, x0
    mov     x0, #1
    bl      _write
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


def _bss(user_memory_bytes: int) -> str:
    user_size = max(USER_MEMORY_MIN_BYTES, _round_up_16(user_memory_bytes))
    return (
        f"\n.zerofill __DATA,__bss,Ldstack_base,{DSTACK_BYTES},3\n"
        f".zerofill __DATA,__bss,Luser_mem,{user_size},3\n"
    )


def _round_up_16(n: int) -> int:
    return (n + 15) & ~15
