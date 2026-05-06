"""Smoke test: JIT-compile '2 3 +' through the IR emitter, run via Unicorn.

Runs anywhere with unicorn installed (no Apple Silicon, no clang, no JIT
entitlement needed). Validates that the emitter produces bytes that
actually execute correctly against stub primitives.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mzt.ir import Literal, PrimRef
from mzt.jit.assembler import (
    encode_add_reg,
    encode_ldr_post_imm,
    encode_ret,
    encode_str_pre_imm,
    words_to_bytes,
)
from mzt.jit.emitter import compile_body_to_bytes
from mzt.jit.primitive_table import PrimitiveTable


def _stub_plus_bytes() -> bytes:
    return words_to_bytes([
        encode_ldr_post_imm(0, 19, 8),
        encode_ldr_post_imm(1, 19, 8),
        encode_add_reg(0, 1, 0),
        encode_str_pre_imm(0, 19, -8),
        encode_ret(),
    ])


def main() -> int:
    try:
        from tests.jit_runner import JIT_BASE, PRIM_BASE, run_jit_body
    except ImportError as exc:
        print(f"unicorn not available: {exc}")
        return 1

    plus_addr = PRIM_BASE
    table = PrimitiveTable({"+": plus_addr})

    cells = [Literal(2), Literal(3), PrimRef("+")]
    body = compile_body_to_bytes(cells, base_addr=JIT_BASE, primitives=table)

    print(f"emitted {len(body)} bytes for IR cells: {[type(c).__name__ for c in cells]}")
    result = run_jit_body(body, primitive_stubs={plus_addr: _stub_plus_bytes()})

    print(f"executed; data stack = {result}")
    return 0 if result == [5] else 1


if __name__ == "__main__":
    sys.exit(main())
