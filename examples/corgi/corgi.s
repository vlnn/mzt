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

_key:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    sub     sp, sp, #16
    mov     x0, #0
    mov     x1, sp
    mov     x2, #1
    bl      _read
    ldrb    w1, [sp]
    mov     x2, #-1
    cmp     x0, #1
    csel    x0, x1, x2, eq
    str     x0, [x19, #-8]!
    add     sp, sp, #16
    ldp     x29, x30, [sp], #16
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

_word__slash_cell:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =8
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word__slash_room:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =40
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word__dot_exits:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word__dot_description:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =32
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_bone:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_stick:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_ball:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =2
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word__slash_items:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =3
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_nowhere:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_carried:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-2
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_dir_n:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_dir_s:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_dir_e:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =2
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_dir_w:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =3
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_opposite_dir:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _xor
    ldp     x29, x30, [sp], #16
    ret

_word_kitchen_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_0@PAGE
    add     x0, x0, Lstr_0@PAGEOFF
    mov     x1, #29
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_1@PAGE
    add     x0, x0, Lstr_1@PAGEOFF
    mov     x1, #35
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_2@PAGE
    add     x0, x0, Lstr_2@PAGEOFF
    mov     x1, #35
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_hallway_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_3@PAGE
    add     x0, x0, Lstr_3@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_4@PAGE
    add     x0, x0, Lstr_4@PAGEOFF
    mov     x1, #28
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_5@PAGE
    add     x0, x0, Lstr_5@PAGEOFF
    mov     x1, #47
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_garden_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_6@PAGE
    add     x0, x0, Lstr_6@PAGEOFF
    mov     x1, #27
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_7@PAGE
    add     x0, x0, Lstr_7@PAGEOFF
    mov     x1, #26
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_8@PAGE
    add     x0, x0, Lstr_8@PAGEOFF
    mov     x1, #43
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_road_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_9@PAGE
    add     x0, x0, Lstr_9@PAGEOFF
    mov     x1, #21
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_10@PAGE
    add     x0, x0, Lstr_10@PAGEOFF
    mov     x1, #25
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_11@PAGE
    add     x0, x0, Lstr_11@PAGEOFF
    mov     x1, #41
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_well_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_12@PAGE
    add     x0, x0, Lstr_12@PAGEOFF
    mov     x1, #25
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_13@PAGE
    add     x0, x0, Lstr_13@PAGEOFF
    mov     x1, #40
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_14@PAGE
    add     x0, x0, Lstr_14@PAGEOFF
    mov     x1, #29
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_kitchen:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_hallway:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #40
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_garden:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #80
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_road:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #120
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_well:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #160
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_exit_cell:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word__slash_cell
    bl      _star
    bl      _swap
    bl      _word__dot_exits
    bl      _plus
    bl      _plus
    ldp     x29, x30, [sp], #16
    ret

_word_exit_of:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_exit_cell
    bl      _fetch
    ldp     x29, x30, [sp], #16
    ret

_word_blocked_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _eq
    ldp     x29, x30, [sp], #16
    ret

_word_connect:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_exit_cell
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_connect_pair:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _to_r
    bl      _word_2dup
    bl      _swap
    bl      _r_fetch
    bl      _word_connect
    bl      _r_from
    bl      _word_opposite_dir
    bl      _word_connect
    ldp     x29, x30, [sp], #16
    ret

_word_clear_exits:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _over
    bl      _word__dot_exits
    bl      _plus
    bl      _store
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _over
    bl      _word__dot_exits
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _plus
    bl      _plus
    bl      _store
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _over
    bl      _word__dot_exits
    ldr     x0, =16
    str     x0, [x19, #-8]!
    bl      _plus
    bl      _plus
    bl      _store
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _over
    bl      _word__dot_exits
    ldr     x0, =24
    str     x0, [x19, #-8]!
    bl      _plus
    bl      _plus
    bl      _store
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_install_desc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word__dot_description
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_install_edges:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_kitchen
    bl      _word_hallway
    bl      _word_dir_n
    bl      _word_connect_pair
    bl      _word_hallway
    bl      _word_garden
    bl      _word_dir_n
    bl      _word_connect_pair
    bl      _word_garden
    bl      _word_road
    bl      _word_dir_n
    bl      _word_connect_pair
    bl      _word_road
    bl      _word_well
    bl      _word_dir_e
    bl      _word_connect_pair
    ldp     x29, x30, [sp], #16
    ret

_word_reset_room_exits:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_kitchen
    bl      _word_clear_exits
    bl      _word_hallway
    bl      _word_clear_exits
    bl      _word_garden
    bl      _word_clear_exits
    bl      _word_road
    bl      _word_clear_exits
    bl      _word_well
    bl      _word_clear_exits
    ldp     x29, x30, [sp], #16
    ret

_word_setup_rooms:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_reset_room_exits
    bl      _word_install_edges
    adrp    x0, _word___noname_0@PAGE
    add     x0, x0, _word___noname_0@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_kitchen
    bl      _word_install_desc
    adrp    x0, _word___noname_1@PAGE
    add     x0, x0, _word___noname_1@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_hallway
    bl      _word_install_desc
    adrp    x0, _word___noname_2@PAGE
    add     x0, x0, _word___noname_2@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_garden
    bl      _word_install_desc
    adrp    x0, _word___noname_3@PAGE
    add     x0, x0, _word___noname_3@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_road
    bl      _word_install_desc
    adrp    x0, _word___noname_4@PAGE
    add     x0, x0, _word___noname_4@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_well
    bl      _word_install_desc
    ldp     x29, x30, [sp], #16
    ret

_word_init_exits:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_setup_rooms
    ldp     x29, x30, [sp], #16
    ret

_word_here_room:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #200
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_item_loc:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #208
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_item_homes:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #232
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_item_room_fetch_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_loc
    bl      _plus
    bl      _fetch
    ldp     x29, x30, [sp], #16
    ret

_word_item_room_store_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_loc
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_setup_item_homes:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_kitchen
    str     xzr, [x19, #-8]!
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_homes
    bl      _plus
    bl      _store
    bl      _word_garden
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_homes
    bl      _plus
    bl      _store
    bl      _word_well
    ldr     x0, =2
    str     x0, [x19, #-8]!
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_homes
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_place_items:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_setup_item_homes
    bl      _word__slash_items
    str     xzr, [x19, #-8]!
    bl      _do_init
L7:
    bl      _loop_i
    bl      _word__slash_cell
    bl      _star
    bl      _word_item_homes
    bl      _plus
    bl      _fetch
    bl      _loop_i
    bl      _word_item_room_store_
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L7
L8:
    bl      _unloop
    ldp     x29, x30, [sp], #16
    ret

_word_in_room_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _swap
    bl      _word_item_room_fetch_
    bl      _eq
    ldp     x29, x30, [sp], #16
    ret

_word_room_has_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_in_room_q_
    ldp     x29, x30, [sp], #16
    ret

_word_carrying_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_item_room_fetch_
    bl      _word_carried
    bl      _eq
    ldp     x29, x30, [sp], #16
    ret

_word_have_stick_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_stick
    bl      _word_carrying_q_
    ldp     x29, x30, [sp], #16
    ret

_word_here_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_item_room_fetch_
    bl      _word_here_room
    bl      _fetch
    bl      _eq
    ldp     x29, x30, [sp], #16
    ret

_word___pick_result:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #256
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_pick_at:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _word___pick_result
    bl      _store
    bl      _word__slash_items
    str     xzr, [x19, #-8]!
    bl      _do_init
L9:
    bl      _dup
    bl      _loop_i
    bl      _word_item_room_fetch_
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L11
    bl      _loop_i
    bl      _word___pick_result
    bl      _store
    b       L10
L11:
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L9
L10:
    bl      _unloop
    bl      _drop
    bl      _word___pick_result
    bl      _fetch
    ldp     x29, x30, [sp], #16
    ret

_word_game_over:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #264
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_bone_name:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_15@PAGE
    add     x0, x0, Lstr_15@PAGEOFF
    mov     x1, #4
    bl      _print_str
    ldp     x29, x30, [sp], #16
    ret

_word_stick_name:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_16@PAGE
    add     x0, x0, Lstr_16@PAGEOFF
    mov     x1, #5
    bl      _print_str
    ldp     x29, x30, [sp], #16
    ret

_word_ball_name:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_17@PAGE
    add     x0, x0, Lstr_17@PAGEOFF
    mov     x1, #8
    bl      _print_str
    ldp     x29, x30, [sp], #16
    ret

_word_item_printers:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #272
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_install_item_printer:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_item_printers
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_setup_item_printers:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, _word___noname_5@PAGE
    add     x0, x0, _word___noname_5@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_bone
    bl      _word_install_item_printer
    adrp    x0, _word___noname_6@PAGE
    add     x0, x0, _word___noname_6@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_stick
    bl      _word_install_item_printer
    adrp    x0, _word___noname_7@PAGE
    add     x0, x0, _word___noname_7@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_ball
    bl      _word_install_item_printer
    ldp     x29, x30, [sp], #16
    ret

_word_print_item_name:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_item_printers
    bl      _plus
    bl      _fetch
    bl      _execute
    ldp     x29, x30, [sp], #16
    ret

_word_announce_here:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_18@PAGE
    add     x0, x0, Lstr_18@PAGEOFF
    mov     x1, #11
    bl      _print_str
    bl      _word_print_item_name
    adrp    x0, Lstr_19@PAGE
    add     x0, x0, Lstr_19@PAGEOFF
    mov     x1, #5
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_with_space:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_item_name
    bl      _word_space
    ldp     x29, x30, [sp], #16
    ret

_word_any_carried_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #296
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_describe_room:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_here_room
    bl      _fetch
    bl      _word__dot_description
    bl      _plus
    bl      _fetch
    bl      _execute
    ldp     x29, x30, [sp], #16
    ret

_word_list_items_here:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word__slash_items
    str     xzr, [x19, #-8]!
    bl      _do_init
L12:
    bl      _loop_i
    bl      _word_here_q_
    ldr     x0, [x19], #8
    cbz     x0, L14
    bl      _loop_i
    bl      _word_announce_here
L14:
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L12
L13:
    bl      _unloop
    ldp     x29, x30, [sp], #16
    ret

_word_list_inventory:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_20@PAGE
    add     x0, x0, Lstr_20@PAGEOFF
    mov     x1, #18
    bl      _print_str
    str     xzr, [x19, #-8]!
    bl      _word_any_carried_q_
    bl      _store
    bl      _word__slash_items
    str     xzr, [x19, #-8]!
    bl      _do_init
L15:
    bl      _loop_i
    bl      _word_carrying_q_
    ldr     x0, [x19], #8
    cbz     x0, L17
    bl      _loop_i
    bl      _word_print_with_space
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word_any_carried_q_
    bl      _store
L17:
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L15
L16:
    bl      _unloop
    bl      _word_any_carried_q_
    bl      _fetch
    bl      _zeq
    ldr     x0, [x19], #8
    cbz     x0, L18
    adrp    x0, Lstr_21@PAGE
    add     x0, x0, Lstr_21@PAGEOFF
    mov     x1, #8
    bl      _print_str
L18:
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_look_here:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_describe_room
    bl      _word_list_items_here
    ldp     x29, x30, [sp], #16
    ret

_word_key_n:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =110
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_s:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =115
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_e:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =101
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_w:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =119
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_l:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =108
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_t:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =116
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_g:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =103
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_d:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =100
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_i:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =105
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_b:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =98
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_h:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =104
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key__q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =63
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_key_q:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =113
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_last_msg:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #304
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_last_item:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #312
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_show_inv_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #320
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_welcome:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_no_exit:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_too_scary:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =2
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_bravely_east:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =3
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_took:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =4
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_dropped:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =5
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_nothing_here:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =6
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_jaws_empty:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =7
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_bark:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =8
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_help:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =9
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_unknown:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =10
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_quiet:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =11
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_msg_celebrate:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =12
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word__slash_msgs:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =13
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_print_took:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_22@PAGE
    add     x0, x0, Lstr_22@PAGEOFF
    mov     x1, #13
    bl      _print_str
    bl      _word_last_item
    bl      _fetch
    bl      _word_print_item_name
    adrp    x0, Lstr_23@PAGE
    add     x0, x0, Lstr_23@PAGEOFF
    mov     x1, #1
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_dropped:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_24@PAGE
    add     x0, x0, Lstr_24@PAGEOFF
    mov     x1, #13
    bl      _print_str
    bl      _word_last_item
    bl      _fetch
    bl      _word_print_item_name
    adrp    x0, Lstr_25@PAGE
    add     x0, x0, Lstr_25@PAGEOFF
    mov     x1, #1
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_welcome:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_26@PAGE
    add     x0, x0, Lstr_26@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_no_exit:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_27@PAGE
    add     x0, x0, Lstr_27@PAGEOFF
    mov     x1, #43
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_too_scary:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_28@PAGE
    add     x0, x0, Lstr_28@PAGEOFF
    mov     x1, #46
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_brave:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_29@PAGE
    add     x0, x0, Lstr_29@PAGEOFF
    mov     x1, #43
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_nothing:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_30@PAGE
    add     x0, x0, Lstr_30@PAGEOFF
    mov     x1, #30
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_empty:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_31@PAGE
    add     x0, x0, Lstr_31@PAGEOFF
    mov     x1, #20
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_bark:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_32@PAGE
    add     x0, x0, Lstr_32@PAGEOFF
    mov     x1, #5
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_unknown:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_33@PAGE
    add     x0, x0, Lstr_33@PAGEOFF
    mov     x1, #29
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_quiet:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldp     x29, x30, [sp], #16
    ret

_word_print_celebrate:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _cr
    adrp    x0, Lstr_34@PAGE
    add     x0, x0, Lstr_34@PAGEOFF
    mov     x1, #19
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_35@PAGE
    add     x0, x0, Lstr_35@PAGEOFF
    mov     x1, #26
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_36@PAGE
    add     x0, x0, Lstr_36@PAGEOFF
    mov     x1, #26
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_print_help:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_37@PAGE
    add     x0, x0, Lstr_37@PAGEOFF
    mov     x1, #31
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_38@PAGE
    add     x0, x0, Lstr_38@PAGEOFF
    mov     x1, #23
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_39@PAGE
    add     x0, x0, Lstr_39@PAGEOFF
    mov     x1, #43
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_40@PAGE
    add     x0, x0, Lstr_40@PAGEOFF
    mov     x1, #33
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_41@PAGE
    add     x0, x0, Lstr_41@PAGEOFF
    mov     x1, #31
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_42@PAGE
    add     x0, x0, Lstr_42@PAGEOFF
    mov     x1, #26
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_43@PAGE
    add     x0, x0, Lstr_43@PAGEOFF
    mov     x1, #21
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_44@PAGE
    add     x0, x0, Lstr_44@PAGEOFF
    mov     x1, #17
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_45@PAGE
    add     x0, x0, Lstr_45@PAGEOFF
    mov     x1, #21
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_46@PAGE
    add     x0, x0, Lstr_46@PAGEOFF
    mov     x1, #25
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_msg_printers:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #328
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_install_msg:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_msg_printers
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_setup_msg_printers:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, _word___noname_8@PAGE
    add     x0, x0, _word___noname_8@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_welcome
    bl      _word_install_msg
    adrp    x0, _word___noname_9@PAGE
    add     x0, x0, _word___noname_9@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_no_exit
    bl      _word_install_msg
    adrp    x0, _word___noname_10@PAGE
    add     x0, x0, _word___noname_10@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_too_scary
    bl      _word_install_msg
    adrp    x0, _word___noname_11@PAGE
    add     x0, x0, _word___noname_11@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_bravely_east
    bl      _word_install_msg
    adrp    x0, _word___noname_12@PAGE
    add     x0, x0, _word___noname_12@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_took
    bl      _word_install_msg
    adrp    x0, _word___noname_13@PAGE
    add     x0, x0, _word___noname_13@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_dropped
    bl      _word_install_msg
    adrp    x0, _word___noname_14@PAGE
    add     x0, x0, _word___noname_14@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_nothing_here
    bl      _word_install_msg
    adrp    x0, _word___noname_15@PAGE
    add     x0, x0, _word___noname_15@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_jaws_empty
    bl      _word_install_msg
    adrp    x0, _word___noname_16@PAGE
    add     x0, x0, _word___noname_16@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_bark
    bl      _word_install_msg
    adrp    x0, _word___noname_17@PAGE
    add     x0, x0, _word___noname_17@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_help
    bl      _word_install_msg
    adrp    x0, _word___noname_18@PAGE
    add     x0, x0, _word___noname_18@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_unknown
    bl      _word_install_msg
    adrp    x0, _word___noname_19@PAGE
    add     x0, x0, _word___noname_19@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_quiet
    bl      _word_install_msg
    adrp    x0, _word___noname_20@PAGE
    add     x0, x0, _word___noname_20@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_msg_celebrate
    bl      _word_install_msg
    ldp     x29, x30, [sp], #16
    ret

_word_show_msg:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_last_msg
    bl      _fetch
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_msg_printers
    bl      _plus
    bl      _fetch
    bl      _execute
    ldp     x29, x30, [sp], #16
    ret

_word_maybe_inventory:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_show_inv_q_
    bl      _fetch
    ldr     x0, [x19], #8
    cbz     x0, L19
    str     xzr, [x19, #-8]!
    bl      _word_show_inv_q_
    bl      _store
    bl      _word_list_inventory
L19:
    ldp     x29, x30, [sp], #16
    ret

_word_try_go:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_here_room
    bl      _fetch
    bl      _swap
    bl      _word_exit_of
    bl      _dup
    bl      _word_blocked_q_
    ldr     x0, [x19], #8
    cbz     x0, L20
    bl      _drop
    bl      _word_msg_no_exit
    bl      _word_last_msg
    bl      _store
    b       L21
L20:
    bl      _word_here_room
    bl      _store
    bl      _word_msg_quiet
    bl      _word_last_msg
    bl      _store
L21:
    ldp     x29, x30, [sp], #16
    ret

_word_try_east_from_road:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_have_stick_q_
    ldr     x0, [x19], #8
    cbz     x0, L22
    bl      _word_well
    bl      _word_here_room
    bl      _store
    bl      _word_msg_bravely_east
    bl      _word_last_msg
    bl      _store
    b       L23
L22:
    bl      _word_msg_too_scary
    bl      _word_last_msg
    bl      _store
L23:
    ldp     x29, x30, [sp], #16
    ret

_word_do_east:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_here_room
    bl      _fetch
    bl      _word_road
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L24
    bl      _word_try_east_from_road
    b       L25
L24:
    bl      _word_dir_e
    bl      _word_try_go
L25:
    ldp     x29, x30, [sp], #16
    ret

_word_do_north:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_dir_n
    bl      _word_try_go
    ldp     x29, x30, [sp], #16
    ret

_word_do_south:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_dir_s
    bl      _word_try_go
    ldp     x29, x30, [sp], #16
    ret

_word_do_west:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_dir_w
    bl      _word_try_go
    ldp     x29, x30, [sp], #16
    ret

_word_pick_here:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_here_room
    bl      _fetch
    bl      _word_pick_at
    ldp     x29, x30, [sp], #16
    ret

_word_pick_carried:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_carried
    bl      _word_pick_at
    ldp     x29, x30, [sp], #16
    ret

_word_do_take:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_pick_here
    bl      _dup
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L26
    bl      _drop
    bl      _word_msg_nothing_here
    bl      _word_last_msg
    bl      _store
    b       L27
L26:
    bl      _dup
    bl      _word_last_item
    bl      _store
    bl      _word_carried
    bl      _swap
    bl      _word_item_room_store_
    bl      _word_msg_took
    bl      _word_last_msg
    bl      _store
L27:
    ldp     x29, x30, [sp], #16
    ret

_word_do_drop:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_pick_carried
    bl      _dup
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L28
    bl      _drop
    bl      _word_msg_jaws_empty
    bl      _word_last_msg
    bl      _store
    b       L29
L28:
    bl      _dup
    bl      _word_last_item
    bl      _store
    bl      _word_here_room
    bl      _fetch
    bl      _swap
    bl      _word_item_room_store_
    bl      _word_msg_dropped
    bl      _word_last_msg
    bl      _store
L29:
    ldp     x29, x30, [sp], #16
    ret

_word_do_bark:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_bark
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_look:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_quiet
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_help:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_help
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_quit:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word_game_over
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_inventory:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word_show_inv_q_
    bl      _store
    bl      _word_msg_quiet
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_empty:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_quiet
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_do_unknown:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_unknown
    bl      _word_last_msg
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word__slash_commands:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =14
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_cmd_keys:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #432
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_cmd_actions:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #446
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_install_cmd:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _to_r
    bl      _r_fetch
    bl      _word_cmd_keys
    bl      _plus
    bl      _cstore
    bl      _r_from
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_cmd_actions
    bl      _plus
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_setup_commands:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, _word___noname_21@PAGE
    add     x0, x0, _word___noname_21@PAGEOFF
    str     x0, [x19, #-8]!
    str     xzr, [x19, #-8]!
    str     xzr, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_22@PAGE
    add     x0, x0, _word___noname_22@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_n
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_23@PAGE
    add     x0, x0, _word___noname_23@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_s
    ldr     x0, =2
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_24@PAGE
    add     x0, x0, _word___noname_24@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_e
    ldr     x0, =3
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_25@PAGE
    add     x0, x0, _word___noname_25@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_w
    ldr     x0, =4
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_26@PAGE
    add     x0, x0, _word___noname_26@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_l
    ldr     x0, =5
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_27@PAGE
    add     x0, x0, _word___noname_27@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_t
    ldr     x0, =6
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_28@PAGE
    add     x0, x0, _word___noname_28@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_g
    ldr     x0, =7
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_29@PAGE
    add     x0, x0, _word___noname_29@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_d
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_30@PAGE
    add     x0, x0, _word___noname_30@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_i
    ldr     x0, =9
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_31@PAGE
    add     x0, x0, _word___noname_31@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_b
    ldr     x0, =10
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_32@PAGE
    add     x0, x0, _word___noname_32@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_h
    ldr     x0, =11
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_33@PAGE
    add     x0, x0, _word___noname_33@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key__q_
    ldr     x0, =12
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    adrp    x0, _word___noname_34@PAGE
    add     x0, x0, _word___noname_34@PAGEOFF
    str     x0, [x19, #-8]!
    bl      _word_key_q
    ldr     x0, =13
    str     x0, [x19, #-8]!
    bl      _word_install_cmd
    ldp     x29, x30, [sp], #16
    ret

_word___cmd_found:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #558
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_lookup_cmd:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _word___cmd_found
    bl      _store
    bl      _word__slash_commands
    str     xzr, [x19, #-8]!
    bl      _do_init
L30:
    bl      _dup
    bl      _loop_i
    bl      _word_cmd_keys
    bl      _plus
    bl      _cfetch
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L32
    bl      _loop_i
    bl      _word___cmd_found
    bl      _store
    b       L31
L32:
    bl      _loop_test
    ldr     x0, [x19], #8
    cbz     x0, L30
L31:
    bl      _unloop
    bl      _drop
    bl      _word___cmd_found
    bl      _fetch
    ldp     x29, x30, [sp], #16
    ret

_word_dispatch:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_lookup_cmd
    bl      _dup
    ldr     x0, =-1
    str     x0, [x19, #-8]!
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L33
    bl      _drop
    bl      _word_do_unknown
    b       L34
L33:
    ldr     x0, =8
    str     x0, [x19, #-8]!
    bl      _star
    bl      _word_cmd_actions
    bl      _plus
    bl      _fetch
    bl      _execute
L34:
    ldp     x29, x30, [sp], #16
    ret

_word_ansi_clear:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    ldr     x0, =27
    str     x0, [x19, #-8]!
    bl      _emit
    adrp    x0, Lstr_47@PAGE
    add     x0, x0, Lstr_47@PAGEOFF
    mov     x1, #3
    bl      _print_str
    ldr     x0, =27
    str     x0, [x19, #-8]!
    bl      _emit
    adrp    x0, Lstr_48@PAGE
    add     x0, x0, Lstr_48@PAGEOFF
    mov     x1, #2
    bl      _print_str
    ldp     x29, x30, [sp], #16
    ret

_word_prompt:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Lstr_49@PAGE
    add     x0, x0, Lstr_49@PAGEOFF
    mov     x1, #2
    bl      _print_str
    ldp     x29, x30, [sp], #16
    ret

_word_render:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_ansi_clear
    bl      _word_show_msg
    bl      _word_maybe_inventory
    bl      _cr
    bl      _word_look_here
    bl      _cr
    bl      _word_prompt
    ldp     x29, x30, [sp], #16
    ret

_word_reset_game:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_setup_rooms
    bl      _word_setup_item_printers
    bl      _word_setup_msg_printers
    bl      _word_setup_commands
    str     xzr, [x19, #-8]!
    bl      _word_game_over
    bl      _store
    str     xzr, [x19, #-8]!
    bl      _word_show_inv_q_
    bl      _store
    bl      _word_msg_welcome
    bl      _word_last_msg
    bl      _store
    bl      _word_kitchen
    bl      _word_here_room
    bl      _store
    bl      _word_place_items
    ldp     x29, x30, [sp], #16
    ret

_word_won_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_ball
    bl      _word_item_room_fetch_
    bl      _word_kitchen
    bl      _eq
    ldp     x29, x30, [sp], #16
    ret

_word_celebrate:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_msg_celebrate
    bl      _word_last_msg
    bl      _store
    ldr     x0, =1
    str     x0, [x19, #-8]!
    bl      _word_game_over
    bl      _store
    ldp     x29, x30, [sp], #16
    ret

_word_ascii_upper_q_:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _dup
    ldr     x0, =64
    str     x0, [x19, #-8]!
    bl      _gt
    bl      _swap
    ldr     x0, =91
    str     x0, [x19, #-8]!
    bl      _lt
    bl      _and
    ldp     x29, x30, [sp], #16
    ret

_word_lower:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _dup
    bl      _word_ascii_upper_q_
    ldr     x0, [x19], #8
    cbz     x0, L35
    ldr     x0, =32
    str     x0, [x19, #-8]!
    bl      _plus
L35:
    ldp     x29, x30, [sp], #16
    ret

_word_input_first:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    adrp    x0, Luser_mem@PAGE
    add     x0, x0, Luser_mem@PAGEOFF
    add     x0, x0, #566
    str     x0, [x19, #-8]!
    ldp     x29, x30, [sp], #16
    ret

_word_read_line_first:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    str     xzr, [x19, #-8]!
    bl      _word_input_first
    bl      _store
L36:
    bl      _key
    bl      _dup
    ldr     x0, =10
    str     x0, [x19, #-8]!
    bl      _eq
    ldr     x0, [x19], #8
    cbz     x0, L37
    bl      _drop
    ldr     x0, =1
    str     x0, [x19, #-8]!
    b       L38
L37:
    bl      _dup
    ldr     x0, =32
    str     x0, [x19, #-8]!
    bl      _eq
    bl      _zeq
    bl      _word_input_first
    bl      _fetch
    bl      _zeq
    bl      _and
    ldr     x0, [x19], #8
    cbz     x0, L39
    bl      _word_input_first
    bl      _store
    b       L40
L39:
    bl      _drop
L40:
    str     xzr, [x19, #-8]!
L38:
    ldr     x0, [x19], #8
    cbz     x0, L36
    bl      _word_input_first
    bl      _fetch
    bl      _word_lower
    ldp     x29, x30, [sp], #16
    ret

_word_intro:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_ansi_clear
    adrp    x0, Lstr_50@PAGE
    add     x0, x0, Lstr_50@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    bl      _cr
    adrp    x0, Lstr_51@PAGE
    add     x0, x0, Lstr_51@PAGEOFF
    mov     x1, #46
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_52@PAGE
    add     x0, x0, Lstr_52@PAGEOFF
    mov     x1, #47
    bl      _print_str
    bl      _cr
    bl      _cr
    adrp    x0, Lstr_53@PAGE
    add     x0, x0, Lstr_53@PAGEOFF
    mov     x1, #45
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_54@PAGE
    add     x0, x0, Lstr_54@PAGEOFF
    mov     x1, #43
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_55@PAGE
    add     x0, x0, Lstr_55@PAGEOFF
    mov     x1, #31
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_56@PAGE
    add     x0, x0, Lstr_56@PAGEOFF
    mov     x1, #26
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_57@PAGE
    add     x0, x0, Lstr_57@PAGEOFF
    mov     x1, #23
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_58@PAGE
    add     x0, x0, Lstr_58@PAGEOFF
    mov     x1, #21
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_59@PAGE
    add     x0, x0, Lstr_59@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_60@PAGE
    add     x0, x0, Lstr_60@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    adrp    x0, Lstr_61@PAGE
    add     x0, x0, Lstr_61@PAGEOFF
    mov     x1, #16
    bl      _print_str
    bl      _cr
    bl      _cr
    adrp    x0, Lstr_62@PAGE
    add     x0, x0, Lstr_62@PAGEOFF
    mov     x1, #23
    bl      _print_str
    bl      _cr
    bl      _word_read_line_first
    bl      _drop
    ldp     x29, x30, [sp], #16
    ret

_word_closing:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_ansi_clear
    bl      _word_show_msg
    bl      _cr
    adrp    x0, Lstr_63@PAGE
    add     x0, x0, Lstr_63@PAGEOFF
    mov     x1, #19
    bl      _print_str
    bl      _cr
    ldp     x29, x30, [sp], #16
    ret

_word_turn:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_render
    bl      _word_read_line_first
    bl      _word_dispatch
    ldp     x29, x30, [sp], #16
    ret

_word_run_corgi:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_intro
    bl      _word_reset_game
L41:
    bl      _word_turn
    bl      _word_won_q_
    ldr     x0, [x19], #8
    cbz     x0, L42
    bl      _word_celebrate
L42:
    bl      _word_game_over
    bl      _fetch
    ldr     x0, [x19], #8
    cbz     x0, L41
    bl      _word_closing
    ldp     x29, x30, [sp], #16
    ret

_word_main:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_run_corgi
    ldp     x29, x30, [sp], #16
    ret

_word___noname_0:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_kitchen_desc
    ldp     x29, x30, [sp], #16
    ret

_word___noname_1:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_hallway_desc
    ldp     x29, x30, [sp], #16
    ret

_word___noname_2:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_garden_desc
    ldp     x29, x30, [sp], #16
    ret

_word___noname_3:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_road_desc
    ldp     x29, x30, [sp], #16
    ret

_word___noname_4:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_well_desc
    ldp     x29, x30, [sp], #16
    ret

_word___noname_5:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_bone_name
    ldp     x29, x30, [sp], #16
    ret

_word___noname_6:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_stick_name
    ldp     x29, x30, [sp], #16
    ret

_word___noname_7:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_ball_name
    ldp     x29, x30, [sp], #16
    ret

_word___noname_8:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_welcome
    ldp     x29, x30, [sp], #16
    ret

_word___noname_9:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_no_exit
    ldp     x29, x30, [sp], #16
    ret

_word___noname_10:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_too_scary
    ldp     x29, x30, [sp], #16
    ret

_word___noname_11:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_brave
    ldp     x29, x30, [sp], #16
    ret

_word___noname_12:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_took
    ldp     x29, x30, [sp], #16
    ret

_word___noname_13:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_dropped
    ldp     x29, x30, [sp], #16
    ret

_word___noname_14:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_nothing
    ldp     x29, x30, [sp], #16
    ret

_word___noname_15:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_empty
    ldp     x29, x30, [sp], #16
    ret

_word___noname_16:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_bark
    ldp     x29, x30, [sp], #16
    ret

_word___noname_17:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_help
    ldp     x29, x30, [sp], #16
    ret

_word___noname_18:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_unknown
    ldp     x29, x30, [sp], #16
    ret

_word___noname_19:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_quiet
    ldp     x29, x30, [sp], #16
    ret

_word___noname_20:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_print_celebrate
    ldp     x29, x30, [sp], #16
    ret

_word___noname_21:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_empty
    ldp     x29, x30, [sp], #16
    ret

_word___noname_22:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_north
    ldp     x29, x30, [sp], #16
    ret

_word___noname_23:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_south
    ldp     x29, x30, [sp], #16
    ret

_word___noname_24:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_east
    ldp     x29, x30, [sp], #16
    ret

_word___noname_25:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_west
    ldp     x29, x30, [sp], #16
    ret

_word___noname_26:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_look
    ldp     x29, x30, [sp], #16
    ret

_word___noname_27:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_take
    ldp     x29, x30, [sp], #16
    ret

_word___noname_28:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_take
    ldp     x29, x30, [sp], #16
    ret

_word___noname_29:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_drop
    ldp     x29, x30, [sp], #16
    ret

_word___noname_30:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_inventory
    ldp     x29, x30, [sp], #16
    ret

_word___noname_31:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_bark
    ldp     x29, x30, [sp], #16
    ret

_word___noname_32:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_help
    ldp     x29, x30, [sp], #16
    ret

_word___noname_33:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_help
    ldp     x29, x30, [sp], #16
    ret

_word___noname_34:
    stp     x29, x30, [sp, #-16]!
    mov     x29, sp
    bl      _word_do_quit
    ldp     x29, x30, [sp], #16
    ret


.section __TEXT,__cstring,cstring_literals
Lfmt_dot:
    .asciz  "%lld\n"

.zerofill __DATA,__bss,Ldstack_base,8192,3
.zerofill __DATA,__bss,Lrstack_base,4096,3
.zerofill __DATA,__bss,Luser_mem,576,3

.section __TEXT,__cstring,cstring_literals
Lstr_0:
    .asciz  "You are in your warm kitchen."
Lstr_1:
    .asciz  "Your bowl smells faintly of dinner."
Lstr_2:
    .asciz  "A bright hallway lies to the NORTH."
Lstr_3:
    .asciz  "A sunny hallway."
Lstr_4:
    .asciz  "The kitchen is to the SOUTH."
Lstr_5:
    .asciz  "The front door stands open NORTH to the garden."
Lstr_6:
    .asciz  "Wonderful, wonderful grass!"
Lstr_7:
    .asciz  "The hallway is back SOUTH."
Lstr_8:
    .asciz  "A gap in the fence leads NORTH to the road."
Lstr_9:
    .asciz  "A quiet country road."
Lstr_10:
    .asciz  "The garden is back SOUTH."
Lstr_11:
    .asciz  "An old WELL stands EAST in a misty field."
Lstr_12:
    .asciz  "A deep, dark, scary well."
Lstr_13:
    .asciz  "You can hear faint whimpering far below."
Lstr_14:
    .asciz  "The road is back to the WEST."
Lstr_15:
    .asciz  "bone"
Lstr_16:
    .asciz  "stick"
Lstr_17:
    .asciz  "red ball"
Lstr_18:
    .asciz  "There is a "
Lstr_19:
    .asciz  "here."
Lstr_20:
    .asciz  "You are carrying: "
Lstr_21:
    .asciz  "nothing."
Lstr_22:
    .asciz  "You take the "
Lstr_23:
    .asciz  "."
Lstr_24:
    .asciz  "You drop the "
Lstr_25:
    .asciz  "."
Lstr_26:
    .asciz  "Time for a walk!"
Lstr_27:
    .asciz  "You bonk your snoot. No way that direction."
Lstr_28:
    .asciz  "TOO SCARY! You whimper and pad back to safety."
Lstr_29:
    .asciz  "Holding the stick high, you brave the well."
Lstr_30:
    .asciz  "There is nothing here to take."
Lstr_31:
    .asciz  "Your jaws are empty."
Lstr_32:
    .asciz  "WOOF!"
Lstr_33:
    .asciz  "Awoo? You twirl in confusion."
Lstr_34:
    .asciz  "*** GOOD CORGI! ***"
Lstr_35:
    .asciz  "You brought the ball home."
Lstr_36:
    .asciz  "The puppy upstairs cheers!"
Lstr_37:
    .asciz  "Type a command and press ENTER."
Lstr_38:
    .asciz  "First letter is enough:"
Lstr_39:
    .asciz  "  N S E W   move (north, south, east, west)"
Lstr_40:
    .asciz  "  LOOK      describe surroundings"
Lstr_41:
    .asciz  "  TAKE      grab the thing here"
Lstr_42:
    .asciz  "  DROP      drop something"
Lstr_43:
    .asciz  "  INV       inventory"
Lstr_44:
    .asciz  "  BARK      WOOF!"
Lstr_45:
    .asciz  "  HELP      this help"
Lstr_46:
    .asciz  "  QUIT      stop the game"
Lstr_47:
    .asciz  "[2J"
Lstr_48:
    .asciz  "[H"
Lstr_49:
    .asciz  "> "
Lstr_50:
    .asciz  "CORGI ADVENTURES"
Lstr_51:
    .asciz  "A small dog dropped their ball into the spooky"
Lstr_52:
    .asciz  "old well. Be a brave good corgi: bring it home."
Lstr_53:
    .asciz  "Type and press ENTER. First letter is enough:"
Lstr_54:
    .asciz  "  N S E W   move (north, south, east, west)"
Lstr_55:
    .asciz  "  T or G    take the thing here"
Lstr_56:
    .asciz  "  D         drop something"
Lstr_57:
    .asciz  "  L         look around"
Lstr_58:
    .asciz  "  I         inventory"
Lstr_59:
    .asciz  "  B         bark"
Lstr_60:
    .asciz  "  H or ?    help"
Lstr_61:
    .asciz  "  Q         quit"
Lstr_62:
    .asciz  "Press ENTER to start..."
Lstr_63:
    .asciz  "Thanks for playing!"
