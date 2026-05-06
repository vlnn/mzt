INSTR_SIZE = 4

X0 = 0
X1 = 1
X2 = 2
X3 = 3
X4 = 4
X9 = 9
X19 = 19
X20 = 20
X29 = 29
X30 = 30
SP = 31
XZR = 31

COND_EQ = 0x0
COND_NE = 0x1
COND_CS = 0x2
COND_HS = 0x2
COND_CC = 0x3
COND_LO = 0x3
COND_MI = 0x4
COND_PL = 0x5
COND_VS = 0x6
COND_VC = 0x7
COND_HI = 0x8
COND_LS = 0x9
COND_GE = 0xA
COND_LT = 0xB
COND_GT = 0xC
COND_LE = 0xD
COND_AL = 0xE


class EncodingError(ValueError):
    pass


def _check_reg(name: str, reg: int, *, allow_sp: bool = True) -> None:
    upper = 31 if allow_sp else 30
    if not 0 <= reg <= upper:
        raise EncodingError(f"{name} register {reg} out of range [0, {upper}]")


def _check_aligned(name: str, offset_bytes: int) -> None:
    if offset_bytes % INSTR_SIZE != 0:
        raise EncodingError(
            f"{name} offset {offset_bytes} must be a multiple of {INSTR_SIZE} (alignment)"
        )


def _check_range(name: str, value: int, low: int, high: int) -> None:
    if not low <= value <= high:
        raise EncodingError(f"{name} value {value} out of range [{low}, {high}]")


def _signed_field(value: int, bits: int) -> int:
    return value & ((1 << bits) - 1)


def encode_ret(reg: int = X30) -> int:
    _check_reg("ret", reg)
    return 0xD65F0000 | (reg << 5)


def encode_br(reg: int) -> int:
    _check_reg("br", reg)
    return 0xD61F0000 | (reg << 5)


def encode_blr(reg: int) -> int:
    _check_reg("blr", reg)
    return 0xD63F0000 | (reg << 5)


def encode_bl(offset_bytes: int) -> int:
    _check_aligned("bl", offset_bytes)
    imm26 = offset_bytes >> 2
    _check_range("bl", imm26, -(1 << 25), (1 << 25) - 1)
    return 0x94000000 | _signed_field(imm26, 26)


def encode_b(offset_bytes: int) -> int:
    _check_aligned("b", offset_bytes)
    imm26 = offset_bytes >> 2
    _check_range("b", imm26, -(1 << 25), (1 << 25) - 1)
    return 0x14000000 | _signed_field(imm26, 26)


def encode_b_cond(cond: int, offset_bytes: int) -> int:
    _check_range("b.cond cond", cond, 0, 0xF)
    _check_aligned("b.cond", offset_bytes)
    imm19 = offset_bytes >> 2
    _check_range("b.cond", imm19, -(1 << 18), (1 << 18) - 1)
    return 0x54000000 | (_signed_field(imm19, 19) << 5) | cond


def encode_cbz(reg: int, offset_bytes: int) -> int:
    _check_reg("cbz", reg, allow_sp=False)
    _check_aligned("cbz", offset_bytes)
    imm19 = offset_bytes >> 2
    _check_range("cbz", imm19, -(1 << 18), (1 << 18) - 1)
    return 0xB4000000 | (_signed_field(imm19, 19) << 5) | reg


def encode_cbnz(reg: int, offset_bytes: int) -> int:
    _check_reg("cbnz", reg, allow_sp=False)
    _check_aligned("cbnz", offset_bytes)
    imm19 = offset_bytes >> 2
    _check_range("cbnz", imm19, -(1 << 18), (1 << 18) - 1)
    return 0xB5000000 | (_signed_field(imm19, 19) << 5) | reg


def encode_movz(dst: int, imm16: int, shift: int = 0) -> int:
    _check_reg("movz", dst, allow_sp=False)
    _check_range("movz imm16", imm16, 0, 0xFFFF)
    _check_range("movz shift", shift, 0, 48)
    if shift % 16 != 0:
        raise EncodingError(f"movz shift {shift} must be 0, 16, 32, or 48")
    hw = shift // 16
    return 0xD2800000 | (hw << 21) | (imm16 << 5) | dst


def encode_movk(dst: int, imm16: int, shift: int = 0) -> int:
    _check_reg("movk", dst, allow_sp=False)
    _check_range("movk imm16", imm16, 0, 0xFFFF)
    _check_range("movk shift", shift, 0, 48)
    if shift % 16 != 0:
        raise EncodingError(f"movk shift {shift} must be 0, 16, 32, or 48")
    hw = shift // 16
    return 0xF2800000 | (hw << 21) | (imm16 << 5) | dst


def encode_movn(dst: int, imm16: int, shift: int = 0) -> int:
    _check_reg("movn", dst, allow_sp=False)
    _check_range("movn imm16", imm16, 0, 0xFFFF)
    _check_range("movn shift", shift, 0, 48)
    if shift % 16 != 0:
        raise EncodingError(f"movn shift {shift} must be 0, 16, 32, or 48")
    hw = shift // 16
    return 0x92800000 | (hw << 21) | (imm16 << 5) | dst


def encode_add_imm(dst: int, src: int, imm: int) -> int:
    _check_reg("add dst", dst)
    _check_reg("add src", src)
    _check_range("add imm12", imm, 0, 0xFFF)
    return 0x91000000 | (imm << 10) | (src << 5) | dst


def encode_sub_imm(dst: int, src: int, imm: int) -> int:
    _check_reg("sub dst", dst)
    _check_reg("sub src", src)
    _check_range("sub imm12", imm, 0, 0xFFF)
    return 0xD1000000 | (imm << 10) | (src << 5) | dst


def encode_add_reg(dst: int, lhs: int, rhs: int) -> int:
    _check_reg("add dst", dst, allow_sp=False)
    _check_reg("add lhs", lhs, allow_sp=False)
    _check_reg("add rhs", rhs, allow_sp=False)
    return 0x8B000000 | (rhs << 16) | (lhs << 5) | dst


def encode_sub_reg(dst: int, lhs: int, rhs: int) -> int:
    _check_reg("sub dst", dst, allow_sp=False)
    _check_reg("sub lhs", lhs, allow_sp=False)
    _check_reg("sub rhs", rhs, allow_sp=False)
    return 0xCB000000 | (rhs << 16) | (lhs << 5) | dst


def encode_adrp(dst: int, page_offset: int) -> int:
    _check_reg("adrp", dst, allow_sp=False)
    if page_offset % 4096 != 0:
        raise EncodingError(f"adrp page_offset {page_offset} must be a multiple of 4096")
    pages = page_offset >> 12
    _check_range("adrp", pages, -(1 << 20), (1 << 20) - 1)
    immlo = pages & 3
    immhi = (pages >> 2) & 0x7FFFF
    return 0x90000000 | (immlo << 29) | (immhi << 5) | dst


def encode_str_pre_imm(src: int, base: int, imm9: int) -> int:
    _check_reg("str src", src)
    _check_reg("str base", base)
    _check_range("str imm9", imm9, -256, 255)
    return 0xF8000C00 | (_signed_field(imm9, 9) << 12) | (base << 5) | src


def encode_str_post_imm(src: int, base: int, imm9: int) -> int:
    _check_reg("str src", src)
    _check_reg("str base", base)
    _check_range("str imm9", imm9, -256, 255)
    return 0xF8000400 | (_signed_field(imm9, 9) << 12) | (base << 5) | src


def encode_ldr_pre_imm(dst: int, base: int, imm9: int) -> int:
    _check_reg("ldr dst", dst)
    _check_reg("ldr base", base)
    _check_range("ldr imm9", imm9, -256, 255)
    return 0xF8400C00 | (_signed_field(imm9, 9) << 12) | (base << 5) | dst


def encode_ldr_post_imm(dst: int, base: int, imm9: int) -> int:
    _check_reg("ldr dst", dst)
    _check_reg("ldr base", base)
    _check_range("ldr imm9", imm9, -256, 255)
    return 0xF8400400 | (_signed_field(imm9, 9) << 12) | (base << 5) | dst


def encode_str_offset(src: int, base: int, offset_bytes: int) -> int:
    _check_reg("str src", src)
    _check_reg("str base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"str unsigned offset {offset_bytes} must be a multiple of 8")
    imm12 = offset_bytes >> 3
    _check_range("str imm12", imm12, 0, 0xFFF)
    return 0xF9000000 | (imm12 << 10) | (base << 5) | src


def encode_ldr_offset(dst: int, base: int, offset_bytes: int) -> int:
    _check_reg("ldr dst", dst)
    _check_reg("ldr base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"ldr unsigned offset {offset_bytes} must be a multiple of 8")
    imm12 = offset_bytes >> 3
    _check_range("ldr imm12", imm12, 0, 0xFFF)
    return 0xF9400000 | (imm12 << 10) | (base << 5) | dst


def encode_stp_pre(r1: int, r2: int, base: int, offset_bytes: int) -> int:
    _check_reg("stp r1", r1)
    _check_reg("stp r2", r2)
    _check_reg("stp base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"stp offset {offset_bytes} must be a multiple of 8")
    imm7 = offset_bytes >> 3
    _check_range("stp imm7", imm7, -64, 63)
    return 0xA9800000 | (_signed_field(imm7, 7) << 15) | (r2 << 10) | (base << 5) | r1


def encode_stp_offset(r1: int, r2: int, base: int, offset_bytes: int) -> int:
    _check_reg("stp r1", r1)
    _check_reg("stp r2", r2)
    _check_reg("stp base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"stp offset {offset_bytes} must be a multiple of 8")
    imm7 = offset_bytes >> 3
    _check_range("stp imm7", imm7, -64, 63)
    return 0xA9000000 | (_signed_field(imm7, 7) << 15) | (r2 << 10) | (base << 5) | r1


def encode_ldp_post(r1: int, r2: int, base: int, offset_bytes: int) -> int:
    _check_reg("ldp r1", r1)
    _check_reg("ldp r2", r2)
    _check_reg("ldp base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"ldp offset {offset_bytes} must be a multiple of 8")
    imm7 = offset_bytes >> 3
    _check_range("ldp imm7", imm7, -64, 63)
    return 0xA8C00000 | (_signed_field(imm7, 7) << 15) | (r2 << 10) | (base << 5) | r1


def encode_ldp_offset(r1: int, r2: int, base: int, offset_bytes: int) -> int:
    _check_reg("ldp r1", r1)
    _check_reg("ldp r2", r2)
    _check_reg("ldp base", base)
    if offset_bytes % 8 != 0:
        raise EncodingError(f"ldp offset {offset_bytes} must be a multiple of 8")
    imm7 = offset_bytes >> 3
    _check_range("ldp imm7", imm7, -64, 63)
    return 0xA9400000 | (_signed_field(imm7, 7) << 15) | (r2 << 10) | (base << 5) | r1


def encode_cmp_imm(reg: int, imm: int) -> int:
    _check_reg("cmp", reg)
    _check_range("cmp imm12", imm, 0, 0xFFF)
    return 0xF1000000 | (imm << 10) | (reg << 5) | XZR


def encode_cmp_reg(lhs: int, rhs: int) -> int:
    _check_reg("cmp lhs", lhs, allow_sp=False)
    _check_reg("cmp rhs", rhs, allow_sp=False)
    return 0xEB000000 | (rhs << 16) | (lhs << 5) | XZR


def encode_mov_reg(dst: int, src: int) -> int:
    _check_reg("mov dst", dst, allow_sp=False)
    _check_reg("mov src", src, allow_sp=False)
    return 0xAA0003E0 | (src << 16) | dst


def encode_mov_from_sp(dst: int) -> int:
    _check_reg("mov-from-sp dst", dst)
    return encode_add_imm(dst, SP, 0)


def encode_mov_to_sp(src: int) -> int:
    _check_reg("mov-to-sp src", src)
    return encode_add_imm(SP, src, 0)


def words_to_bytes(words) -> bytes:
    out = bytearray()
    for word in words:
        out.extend((word & 0xFFFFFFFF).to_bytes(4, "little"))
    return bytes(out)


def unpack_instructions(blob: bytes) -> list[int]:
    if len(blob) % INSTR_SIZE != 0:
        raise EncodingError(f"blob length {len(blob)} is not a multiple of {INSTR_SIZE}")
    return [
        int.from_bytes(blob[i:i + INSTR_SIZE], "little")
        for i in range(0, len(blob), INSTR_SIZE)
    ]


def movz_imm64(dst: int, value: int) -> list[int]:
    value &= 0xFFFFFFFFFFFFFFFF
    chunks = [
        (value >> 0) & 0xFFFF,
        (value >> 16) & 0xFFFF,
        (value >> 32) & 0xFFFF,
        (value >> 48) & 0xFFFF,
    ]
    nonzero = [(i, c) for i, c in enumerate(chunks) if c != 0]
    if not nonzero:
        return [encode_movz(dst, 0, 0)]
    out = [encode_movz(dst, nonzero[0][1], nonzero[0][0] * 16)]
    for shift_idx, chunk in nonzero[1:]:
        out.append(encode_movk(dst, chunk, shift_idx * 16))
    return out
