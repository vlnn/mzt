.section __TEXT,__text,regular,pure_instructions
.globl  _main
.p2align 2

_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x19, Ldstack_base@PAGE
    add     x19, x19, Ldstack_base@PAGEOFF
    add     x19, x19, #8192
    bl      _word_main
    mov     w0, #0
    ldp     x29, x30, [sp], #16
    ret

_print_str:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    mov     x2, x1
    mov     x1, x0
    mov     x0, #1
    bl      _write
    ldp     x29, x30, [sp], #16
    ret

_dup:
    ldr     x0, [x19]
    str     x0, [x19, #-8]!
    ret

_drop:
    add     x19, x19, #8
    ret

_swap:
    ldp     x0, x1, [x19]
    stp     x1, x0, [x19]
    ret

_over:
    ldr     x0, [x19, #8]
    str     x0, [x19, #-8]!
    ret

_nip:
    ldr     x0, [x19]
    add     x19, x19, #8
    str     x0, [x19]
    ret

_rot:
    ldp     x0, x1, [x19]
    ldr     x2, [x19, #16]
    str     x2, [x19]
    stp     x0, x1, [x19, #8]
    ret

_plus:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    add     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_minus:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    sub     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_star:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    mul     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_divmod:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    sdiv    x2, x1, x0
    msub    x3, x2, x0, x1
    str     x3, [x19, #-8]!
    str     x2, [x19, #-8]!
    ret

_eq:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    cmp     x1, x0
    csetm   x0, eq
    str     x0, [x19, #-8]!
    ret

_lt:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    cmp     x1, x0
    csetm   x0, lt
    str     x0, [x19, #-8]!
    ret

_gt:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    cmp     x1, x0
    csetm   x0, gt
    str     x0, [x19, #-8]!
    ret

_zeq:
    ldr     x0, [x19]
    cmp     x0, #0
    csetm   x0, eq
    str     x0, [x19]
    ret

_and:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    and     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_or:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    orr     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_xor:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    eor     x0, x1, x0
    str     x0, [x19, #-8]!
    ret

_invert:
    ldr     x0, [x19]
    mvn     x0, x0
    str     x0, [x19]
    ret

_negate:
    ldr     x0, [x19]
    neg     x0, x0
    str     x0, [x19]
    ret

_abs:
    ldr     x0, [x19]
    cmp     x0, #0
    cneg    x0, x0, lt
    str     x0, [x19]
    ret

_dot:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x9, [x19], #8
    sub     sp, sp, #16
    str     x9, [sp]
    adrp    x0, Lfmt_dot@PAGE
    add     x0, x0, Lfmt_dot@PAGEOFF
    bl      _printf
    add     sp, sp, #16
    ldp     x29, x30, [sp], #16
    ret

_emit:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    sub     sp, sp, #16
    ldr     x0, [x19], #8
    strb    w0, [sp]
    mov     x0, #1
    mov     x1, sp
    mov     x2, #1
    bl      _write
    add     sp, sp, #16
    ldp     x29, x30, [sp], #16
    ret

_cr:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    sub     sp, sp, #16
    mov     w0, #10
    strb    w0, [sp]
    mov     x0, #1
    mov     x1, sp
    mov     x2, #1
    bl      _write
    add     sp, sp, #16
    ldp     x29, x30, [sp], #16
    ret

_word_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =5
    str     x0, [x19, #-8]!
L0:
    bl      _dup
    bl      _dot
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _minus
    bl      _dup
    bl      _zeq
    ldr     x0, [x19], #8
    cbz     x0, L0
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret


.section __TEXT,__cstring,cstring_literals
Lfmt_dot:
    .asciz  "%lld\n"

.zerofill __DATA,__bss,Ldstack_base,8192,3
