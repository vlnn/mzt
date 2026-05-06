from dataclasses import dataclass

from mzt.ir import Branch, Cell, ColonRef, Label, Literal, PrimRef
from mzt.jit.assembler import (
    encode_b,
    encode_bl,
    encode_blr,
    encode_cbz,
    encode_ldp_post,
    encode_ldr_post_imm,
    encode_mov_from_sp,
    encode_ret,
    encode_stp_pre,
    encode_str_pre_imm,
    movz_imm64,
    words_to_bytes,
)
from mzt.jit.primitive_table import PrimitiveTable
from mzt.primitives import is_primitive, primitive


class JitEmitterError(RuntimeError):
    pass


_INLINE_PRIMITIVE_WORDS: dict[str, list[int]] = {
    "zero": [encode_str_pre_imm(31, 19, -8)],
}


@dataclass(frozen=True)
class _BranchPatch:
    word_index: int
    target_label: int
    conditional: bool


def compile_body(
    cells: list[Cell],
    *,
    base_addr: int,
    primitives: PrimitiveTable,
    word_addresses: dict[str, int] | None = None,
) -> list[int]:
    word_addresses = word_addresses or {}
    words: list[int] = []
    label_positions: dict[int, int] = {}
    patches: list[_BranchPatch] = []

    _emit_prologue(words)
    for cell in cells:
        _emit_cell(
            cell,
            words=words,
            label_positions=label_positions,
            patches=patches,
            base_addr=base_addr,
            primitives=primitives,
            word_addresses=word_addresses,
        )
    _emit_epilogue(words)
    _apply_branch_patches(words, patches, label_positions)
    return words


def compile_body_to_bytes(
    cells: list[Cell],
    *,
    base_addr: int,
    primitives: PrimitiveTable,
    word_addresses: dict[str, int] | None = None,
) -> bytes:
    return words_to_bytes(
        compile_body(
            cells,
            base_addr=base_addr,
            primitives=primitives,
            word_addresses=word_addresses,
        )
    )


def _emit_prologue(words: list[int]) -> None:
    words.append(encode_stp_pre(29, 30, 31, -16))
    words.append(encode_mov_from_sp(29))


def _emit_epilogue(words: list[int]) -> None:
    words.append(encode_ldp_post(29, 30, 31, 16))
    words.append(encode_ret())


def _emit_cell(
    cell: Cell,
    *,
    words: list[int],
    label_positions: dict[int, int],
    patches: list[_BranchPatch],
    base_addr: int,
    primitives: PrimitiveTable,
    word_addresses: dict[str, int],
) -> None:
    if isinstance(cell, Literal):
        _emit_literal(cell, words)
        return
    if isinstance(cell, PrimRef):
        _emit_primref(cell, words, base_addr, primitives)
        return
    if isinstance(cell, ColonRef):
        _emit_colon_ref(cell, words, base_addr, word_addresses)
        return
    if isinstance(cell, Label):
        label_positions[cell.id] = len(words)
        return
    if isinstance(cell, Branch):
        _emit_branch_placeholder(cell, words, patches)
        return
    raise JitEmitterError(f"unsupported IR cell for JIT emitter: {type(cell).__name__}")


def _emit_literal(lit: Literal, words: list[int]) -> None:
    words.extend(movz_imm64(0, lit.value))
    words.append(encode_str_pre_imm(0, 19, -8))


_PRIMITIVE_CALL_REG = 16


def _emit_primref(
    cell: PrimRef,
    words: list[int],
    base_addr: int,
    primitives: PrimitiveTable,
) -> None:
    name = cell.name
    if name in _INLINE_PRIMITIVE_WORDS:
        words.extend(_INLINE_PRIMITIVE_WORDS[name])
        return
    if not primitives.has(name):
        if is_primitive(name) and primitive(name).inline:
            raise JitEmitterError(
                f"inline primitive {name!r} has no JIT body in _INLINE_PRIMITIVE_WORDS; "
                f"add it to mzt.jit.emitter._INLINE_PRIMITIVE_WORDS"
            )
        raise JitEmitterError(f"primitive {name!r} not found in primitive table")
    words.extend(movz_imm64(_PRIMITIVE_CALL_REG, primitives.address(name)))
    words.append(encode_blr(_PRIMITIVE_CALL_REG))


def _emit_colon_ref(
    cell: ColonRef,
    words: list[int],
    base_addr: int,
    word_addresses: dict[str, int],
) -> None:
    if cell.name not in word_addresses:
        raise JitEmitterError(
            f"colon word {cell.name!r} not yet emitted; "
            f"its address is unknown"
        )
    here = base_addr + 4 * len(words)
    words.append(encode_bl(word_addresses[cell.name] - here))


def _emit_branch_placeholder(
    cell: Branch,
    words: list[int],
    patches: list[_BranchPatch],
) -> None:
    if cell.conditional:
        words.append(encode_ldr_post_imm(0, 19, 8))
    patch_index = len(words)
    words.append(0)
    patches.append(_BranchPatch(patch_index, cell.target, cell.conditional))


def _apply_branch_patches(
    words: list[int],
    patches: list[_BranchPatch],
    label_positions: dict[int, int],
) -> None:
    for patch in patches:
        if patch.target_label not in label_positions:
            raise JitEmitterError(
                f"branch targets undefined label id {patch.target_label}"
            )
        target_index = label_positions[patch.target_label]
        offset = (target_index - patch.word_index) * 4
        words[patch.word_index] = (
            encode_cbz(0, offset) if patch.conditional else encode_b(offset)
        )
