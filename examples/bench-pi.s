.section __TEXT,__text,regular,pure_instructions
.globl  _main
.p2align 2

_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x19, Ldstack_base@PAGE
    add     x19, x19, Ldstack_base@PAGEOFF
    add     x19, x19, #8192
    adrp    x20, Lrstack_base@PAGE
    add     x20, x20, Lrstack_base@PAGEOFF
    add     x20, x20, #4096
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

_one_plus:
    ldr     x0, [x19]
    add     x0, x0, #1
    str     x0, [x19]
    ret

_one_minus:
    ldr     x0, [x19]
    sub     x0, x0, #1
    str     x0, [x19]
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

_fetch:
    ldr     x0, [x19]
    ldr     x0, [x0]
    str     x0, [x19]
    ret

_store:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    str     x1, [x0]
    ret

_cfetch:
    ldr     x0, [x19]
    ldrb    w0, [x0]
    str     x0, [x19]
    ret

_cstore:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    strb    w1, [x0]
    ret

_to_r:
    ldr     x0, [x19], #8
    str     x0, [x20, #-8]!
    ret

_r_from:
    ldr     x0, [x20], #8
    str     x0, [x19, #-8]!
    ret

_r_fetch:
    ldr     x0, [x20]
    str     x0, [x19, #-8]!
    ret

_do_init:
    ldr     x0, [x19], #8
    ldr     x1, [x19], #8
    str     x1, [x20, #-8]!
    str     x0, [x20, #-8]!
    ret

_loop_test:
    ldr     x0, [x20]
    add     x0, x0, #1
    str     x0, [x20]
    ldr     x1, [x20, #8]
    cmp     x0, x1
    csetm   x0, eq
    str     x0, [x19, #-8]!
    ret

_plus_loop_test:
    ldr     x0, [x19], #8
    ldr     x1, [x20]
    add     x3, x1, x0
    str     x3, [x20]
    ldr     x2, [x20, #8]
    cmp     x1, x2
    csetm   x4, lt
    cmp     x3, x2
    csetm   x5, lt
    eor     x6, x4, x5
    cmp     x6, #0
    csetm   x0, ne
    str     x0, [x19, #-8]!
    ret

_unloop:
    add     x20, x20, #16
    ret

_loop_i:
    ldr     x0, [x20]
    str     x0, [x19, #-8]!
    ret

_loop_j:
    ldr     x0, [x20, #16]
    str     x0, [x19, #-8]!
    ret

_execute:
    ldr     x9, [x19], #8
    br      x9
    ret

_halt:
    ldr     x0, [x19], #8
    bl      _exit
    ret

_word_2dup:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _over
    bl      _over
    ldp     x29, x30, [sp], #16
    ret

_word_2drop:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _drop
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_tuck:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _swap
    bl      _over
    ldp     x29, x30, [sp], #16
    ret

_word__rot:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _rot
    bl      _rot
    ldp     x29, x30, [sp], #16
    ret

_word__q_dup:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _dup
    ldr     x0, [x19], #8
    cbz     x0, L0
    bl      _dup
L0:
    ldp     x29, x30, [sp], #16
    ret

_word__slash_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _divmod
    bl      _nip
    ldp     x29, x30, [sp], #16
    ret

_word_mod:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _divmod
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_square:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _dup
    bl      _star
    ldp     x29, x30, [sp], #16
    ret

_word_space:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =32
    str     x0, [x19, #-8]!
    bl      _emit
    ldp     x29, x30, [sp], #16
    ret

_word_spaces:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
L1:
    bl      _dup
    str     xzr, [x19, #-8]!
    bl      _gt
    ldr     x0, [x19], #8
    cbz     x0, L2
    bl      _one_minus
    ldr     x0, =32
    str     x0, [x19, #-8]!
    bl      _emit
    b       L1
L2:
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_min:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_2dup
    bl      _lt
    ldr     x0, [x19], #8
    cbz     x0, L3
    bl      _drop
    b       L4
L3:
    bl      _nip
L4:
    ldp     x29, x30, [sp], #16
    ret

_word_max:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_2dup
    bl      _gt
    ldr     x0, [x19], #8
    cbz     x0, L5
    bl      _drop
    b       L6
L5:
    bl      _nip
L6:
    ldp     x29, x30, [sp], #16
    ret

_word_acc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_pi_term:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _over
    ldr     x0, =2
    str     x0, [x19, #-8]!
    bl      _star
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _plus
    bl      _word__slash_
    bl      _swap
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _and
    ldr     x0, [x19], #8
    cbz     x0, L7
    bl      _negate
L7:
    bl      _word_acc
    bl      _fetch
    bl      _plus
    bl      _word_acc
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_pi_loop:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _swap
    str     xzr, [x19, #-8]!
    bl      _do_init
L8:
    bl      _loop_i
    bl      _over
    bl      _word_pi_term
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L8
L9:
    bl      _unloop
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    bl      _word_acc
    bl      _store
    ldr     x0, =1000000
    str     x0, [x19, #-8]!
    ldr     x0, =10000000
    str     x0, [x19, #-8]!
    bl      _word_pi_loop
    bl      _word_acc
    bl      _fetch
    ldr     x0, =4
    str     x0, [x19, #-8]!
    bl      _star
    bl      _dot
    ldp     x29, x30, [sp], #16
    ret


.section __TEXT,__cstring,cstring_literals
Lfmt_dot:
    .asciz  "%lld\n"

.zerofill __DATA,__bss,Ldstack_base,8192,3
.zerofill __DATA,__bss,Lrstack_base,4096,3
.zerofill __DATA,__bss,Luser_mem,16,3
