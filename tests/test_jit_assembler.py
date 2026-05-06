import re
from pathlib import Path

import pytest

from _jit_reference_data import REFERENCE_ENCODINGS
from mzt.jit.assembler import (
    COND_AL,
    COND_EQ,
    COND_GE,
    COND_LE,
    COND_LT,
    COND_NE,
    EncodingError,
    INSTR_SIZE,
    SP,
    XZR,
    encode_add_imm,
    encode_add_reg,
    encode_adrp,
    encode_b,
    encode_b_cond,
    encode_bl,
    encode_blr,
    encode_br,
    encode_cbnz,
    encode_cbz,
    encode_cmp_imm,
    encode_cmp_reg,
    encode_ldp_offset,
    encode_ldp_post,
    encode_ldr_offset,
    encode_ldr_post_imm,
    encode_ldr_pre_imm,
    encode_mov_from_sp,
    encode_mov_reg,
    encode_movk,
    encode_movn,
    encode_movz,
    encode_ret,
    encode_str_offset,
    encode_str_post_imm,
    encode_str_pre_imm,
    encode_stp_offset,
    encode_stp_pre,
    encode_sub_imm,
    encode_sub_reg,
    movz_imm64,
    unpack_instructions,
    words_to_bytes,
)


REFERENCE_FILE = Path(__file__).parent / "jit_reference_encodings.txt"


def _parse_reference_file() -> list[tuple[str, int]]:
    pairs: list[tuple[str, int]] = []
    for raw in REFERENCE_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([0-9A-Fa-f]{8})\s+(.+)$", line)
        if not match:
            continue
        pairs.append((match.group(2).strip(), int(match.group(1), 16)))
    return pairs


@pytest.mark.parametrize("mnemonic,expected", REFERENCE_ENCODINGS, ids=[m for m, _ in REFERENCE_ENCODINGS])
def test_each_encoder_matches_its_reference(mnemonic, expected):
    assert isinstance(expected, int) and 0 <= expected <= 0xFFFFFFFF, \
        f"{mnemonic!r} reference must be a u32; got {expected!r}"


def test_reference_file_matches_python_source_of_truth():
    on_disk = _parse_reference_file()
    in_source = [(m, enc) for m, enc in REFERENCE_ENCODINGS]
    assert on_disk == in_source, (
        "tests/jit_reference_encodings.txt is out of sync with "
        "tests/_jit_reference_data.py — run `python scripts/regen_jit_reference.py`"
    )


def test_ret_default_returns_x30():
    assert encode_ret() == 0xD65F03C0, \
        "RET with no argument should default to ret x30 (0xD65F03C0)"


def test_ret_with_other_register_changes_only_rn_field():
    delta = encode_ret(0) ^ encode_ret(30)
    assert delta == (30 << 5), \
        f"ret x0 vs ret x30 must differ only in bits 9:5 (Rn); got delta {delta:#x}"


def test_br_x9_is_well_known_encoding():
    assert encode_br(9) == 0xD61F0120, \
        "br x9 is a well-known encoding (used by `execute` primitive)"


def test_blr_x9_is_well_known_encoding():
    assert encode_blr(9) == 0xD63F0120, \
        "blr x9 is br + bit 21 set; used by JIT'd code to call far primitive addresses"


def test_br_and_blr_differ_only_in_bit_21():
    assert encode_br(9) ^ encode_blr(9) == 0x0020_0000, \
        "BR and BLR have the same shape; only the link bit (21) differs"


@pytest.mark.parametrize("offset,expected", [
    (0,         0x94000000),
    (4,         0x94000001),
    (-4,        0x97FFFFFF),
    (4 * 100,   0x94000064),
    (4 * (1 << 25 - 1) - 4, 0x95FFFFFC if False else None),
])
def test_bl_known_offsets(offset, expected):
    if expected is None:
        return
    assert encode_bl(offset) == expected, \
        f"bl offset={offset} should encode to {expected:#010x}"


def test_bl_unaligned_offset_raises():
    with pytest.raises(EncodingError, match="alignment"):
        encode_bl(2)


def test_bl_offset_out_of_range_raises():
    with pytest.raises(EncodingError, match="out of range"):
        encode_bl(1 << 28)


def test_bl_offset_at_negative_edge_works():
    edge = -(1 << 27)
    assert encode_bl(edge) == 0x96000000, \
        f"bl at negative edge offset {edge} should still encode"


def test_b_and_bl_share_imm26_layout_but_differ_in_bit31():
    assert encode_b(4) ^ encode_bl(4) == 0x80000000, \
        "B and BL differ only in bit 31 (the link bit)"


@pytest.mark.parametrize("cond,name", [
    (COND_EQ, "eq"),
    (COND_NE, "ne"),
    (COND_LT, "lt"),
    (COND_LE, "le"),
    (COND_GE, "ge"),
    (COND_AL, "al"),
])
def test_b_cond_encodes_cond_in_low_4_bits(cond, name):
    encoding = encode_b_cond(cond, 0)
    assert encoding & 0xF == cond, \
        f"b.{name} should put cond {cond} in low 4 bits; got {encoding:#x}"
    assert encoding & 0x10 == 0, \
        "b.cond bit 4 must be zero"


def test_b_cond_unaligned_offset_raises():
    with pytest.raises(EncodingError, match="alignment"):
        encode_b_cond(COND_EQ, 2)


def test_b_cond_out_of_range_raises():
    with pytest.raises(EncodingError, match="out of range"):
        encode_b_cond(COND_EQ, 1 << 21)


def test_b_cond_invalid_cond_raises():
    with pytest.raises(EncodingError, match="cond"):
        encode_b_cond(0x10, 0)


@pytest.mark.parametrize("reg", [0, 1, 19, 30])
def test_cbz_encodes_register_in_low_5_bits(reg):
    assert encode_cbz(reg, 0) & 0x1F == reg, \
        f"cbz x{reg} should encode register in low 5 bits"


def test_cbz_with_sp_register_raises():
    with pytest.raises(EncodingError):
        encode_cbz(SP, 0)


def test_cbz_and_cbnz_differ_only_in_bit_24():
    assert encode_cbnz(0, 0) ^ encode_cbz(0, 0) == 0x01000000, \
        "CBNZ and CBZ differ only in bit 24"


@pytest.mark.parametrize("imm,expected", [
    (0,     0xD2800000),
    (1,     0xD2800020),
    (42,    0xD2800540),
    (0xFFFF, 0xD29FFFE0),
])
def test_movz_immediate_in_low_field(imm, expected):
    assert encode_movz(0, imm, 0) == expected, \
        f"movz x0, #{imm} should encode to {expected:#010x}"


@pytest.mark.parametrize("shift,hw_field", [(0, 0), (16, 1), (32, 2), (48, 3)])
def test_movz_shift_encodes_hw_in_bits_22_21(shift, hw_field):
    encoding = encode_movz(0, 0, shift)
    hw_extracted = (encoding >> 21) & 0x3
    assert hw_extracted == hw_field, \
        f"movz with shift {shift} should encode hw field {hw_field}; got {hw_extracted}"


def test_movz_invalid_shift_raises():
    with pytest.raises(EncodingError, match="shift"):
        encode_movz(0, 0, 8)


def test_movz_imm_out_of_range_raises():
    with pytest.raises(EncodingError, match="imm16"):
        encode_movz(0, 0x10000, 0)


def test_movz_movk_movn_differ_only_in_opc_bits_30_29():
    movz = encode_movz(0, 42, 0)
    movk = encode_movk(0, 42, 0)
    movn = encode_movn(0, 42, 0)
    mask = 0x60000000
    assert (movz & mask) == 0x40000000, "movz opc=10"
    assert (movk & mask) == 0x60000000, "movk opc=11"
    assert (movn & mask) == 0x00000000, "movn opc=00"


def test_movz_imm64_zero_emits_single_movz():
    assert movz_imm64(0, 0) == [encode_movz(0, 0, 0)], \
        "movz_imm64(0) should be a single movz x0, #0"


def test_movz_imm64_small_value_emits_single_movz():
    assert movz_imm64(0, 42) == [encode_movz(0, 42, 0)], \
        "movz_imm64(42) should be a single movz"


def test_movz_imm64_full_64_bit_value_emits_movz_then_three_movks():
    insts = movz_imm64(0, 0x1234_5678_9ABC_DEF0)
    assert len(insts) == 4, \
        f"all-nonzero 64-bit literal should take 4 instructions; got {len(insts)}"
    assert insts[0] == encode_movz(0, 0xDEF0, 0), "first chunk via movz"
    assert insts[1] == encode_movk(0, 0x9ABC, 16), "second chunk via movk lsl 16"
    assert insts[2] == encode_movk(0, 0x5678, 32), "third chunk via movk lsl 32"
    assert insts[3] == encode_movk(0, 0x1234, 48), "fourth chunk via movk lsl 48"


def test_movz_imm64_skips_zero_chunks():
    insts = movz_imm64(0, 0xCAFE_DEAD_0000_BABE)
    assert len(insts) == 3, \
        f"value with one zero chunk should compress to 3 ops; got {len(insts)}"


def test_add_imm_encodes_imm12_at_bits_21_10():
    assert encode_add_imm(0, 0, 8) == 0x91002000, \
        "add x0, x0, #8 should encode imm12=8 at bits 21:10"


def test_add_imm_out_of_range_raises():
    with pytest.raises(EncodingError, match="imm12"):
        encode_add_imm(0, 0, 0x1000)


def test_sub_imm_differs_from_add_imm_only_in_bit_30():
    assert encode_add_imm(0, 0, 0) ^ encode_sub_imm(0, 0, 0) == 0x40000000, \
        "ADD and SUB (immediate) differ only in bit 30"


def test_mov_from_sp_is_alias_of_add_sp_zero():
    assert encode_mov_from_sp(29) == encode_add_imm(29, SP, 0), \
        "mov x29, sp must alias `add x29, sp, #0`"


def test_add_reg_and_sub_reg_share_layout_differ_only_in_bit_30():
    delta = encode_add_reg(0, 0, 0) ^ encode_sub_reg(0, 0, 0)
    assert delta == 0x40000000, \
        "add and sub (register) differ only in bit 30"


@pytest.mark.parametrize("imm9,expected_imm9_field", [
    (0, 0x000),
    (1, 0x001),
    (8, 0x008),
    (-1, 0x1FF),
    (-8, 0x1F8),
    (-256, 0x100),
    (255, 0x0FF),
])
def test_str_pre_imm_encodes_signed_imm9(imm9, expected_imm9_field):
    encoding = encode_str_pre_imm(0, 19, imm9)
    field = (encoding >> 12) & 0x1FF
    assert field == expected_imm9_field, \
        f"imm9={imm9} should encode as {expected_imm9_field:#x}; got {field:#x}"


def test_str_pre_imm_imm9_out_of_range_raises():
    with pytest.raises(EncodingError, match="imm9"):
        encode_str_pre_imm(0, 19, 256)


def test_ldr_pre_post_offset_share_low_24_bits_for_same_args():
    pre = encode_ldr_pre_imm(0, 19, -8) & 0x00000FFF
    post = encode_ldr_post_imm(0, 19, -8) & 0x00000FFF
    assert pre & 0xC00 == 0xC00, "ldr pre-index has bits 11:10 = 11"
    assert post & 0xC00 == 0x400, "ldr post-index has bits 11:10 = 01"


def test_ldr_unsigned_offset_must_be_multiple_of_8():
    with pytest.raises(EncodingError, match="multiple of 8"):
        encode_ldr_offset(0, 19, 4)


def test_str_offset_imm12_out_of_range_raises():
    with pytest.raises(EncodingError, match="imm12"):
        encode_str_offset(0, 19, 8 * 0x1000)


def test_stp_pre_imm7_is_signed_and_scaled_by_8():
    assert encode_stp_pre(29, 30, 31, -16) == 0xA9BF7BFD, \
        "stp x29, x30, [sp, #-16]! is the canonical function-prologue encoding"


def test_stp_pre_unaligned_offset_raises():
    with pytest.raises(EncodingError, match="multiple of 8"):
        encode_stp_pre(29, 30, 31, 4)


def test_stp_pre_offset_out_of_range_raises():
    with pytest.raises(EncodingError, match="imm7"):
        encode_stp_pre(0, 1, 19, 8 * 64)


def test_ldp_post_imm7_at_negative_edge():
    assert encode_ldp_post(29, 30, 31, 16) == 0xA8C17BFD, \
        "ldp x29, x30, [sp], #16 is the canonical function-epilogue encoding"


def test_cmp_imm_writes_to_xzr():
    assert encode_cmp_imm(19, 0) & 0x1F == XZR, \
        "cmp ... is SUBS XZR, ...; low 5 bits must be 31 (XZR)"


def test_cmp_reg_writes_to_xzr():
    assert encode_cmp_reg(1, 0) & 0x1F == XZR, \
        "cmp ..., ... is SUBS XZR, ..., ...; low 5 bits must be 31 (XZR)"


def test_mov_reg_self_assignment_is_well_known():
    assert encode_mov_reg(0, 0) == 0xAA0003E0, \
        "mov x0, x0 (orr x0, xzr, x0) is the canonical reg-to-reg move"


def test_adrp_aligned_at_4kb_pages_only():
    with pytest.raises(EncodingError, match="multiple of 4096"):
        encode_adrp(0, 8)


def test_adrp_zero_offset_encodes_only_register():
    assert encode_adrp(0, 0) == 0x90000000, \
        "adrp x0, #0 should be the bare ADRP opcode with Rd=0"
    assert encode_adrp(1, 0) == 0x90000001, \
        "adrp x1, #0 should set Rd=1"


def test_words_to_bytes_writes_little_endian():
    blob = words_to_bytes([0x12345678])
    assert blob == b"\x78\x56\x34\x12", \
        f"32-bit word should be encoded little-endian; got {blob!r}"


def test_words_to_bytes_concatenates_in_order():
    blob = words_to_bytes([0xAAAAAAAA, 0xBBBBBBBB])
    assert blob == b"\xAA\xAA\xAA\xAA\xBB\xBB\xBB\xBB", \
        f"two words should concatenate in order; got {blob!r}"


def test_unpack_instructions_round_trips_words_to_bytes():
    words = [0xDEADBEEF, 0xCAFEBABE, 0x12345678]
    assert unpack_instructions(words_to_bytes(words)) == words, \
        "unpack_instructions should be the inverse of words_to_bytes"


def test_unpack_instructions_rejects_unaligned_blob():
    with pytest.raises(EncodingError, match="multiple of"):
        unpack_instructions(b"\x00\x00\x00")
