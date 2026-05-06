#!/usr/bin/env python3
"""Regenerate tests/jit_reference_encodings.txt from the encoder source
of truth in tests/_jit_reference_data.py.

Run after changing any encoder. The output file is the human-readable
audit copy; the actual test source of truth is _jit_reference_data.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from _jit_reference_data import REFERENCE_ENCODINGS


HEADER = """\
# ARM64 reference encodings used by tests/test_jit_assembler.py.
#
# Source of truth: tests/_jit_reference_data.py.
# Regenerate: python scripts/regen_jit_reference.py
# Verify on Apple Silicon: python scripts/verify_jit_encodings.py
#
# Each line: <hex>  <mnemonic>

"""


def main() -> int:
    out_path = ROOT / "tests" / "jit_reference_encodings.txt"
    width = max(len(f"{enc:08X}") for _, enc in REFERENCE_ENCODINGS)
    lines = [HEADER]
    for mnemonic, enc in REFERENCE_ENCODINGS:
        lines.append(f"{enc:08X}  {mnemonic}\n")
    out_path.write_text("".join(lines))
    print(f"wrote {len(REFERENCE_ENCODINGS)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
