"""Round-trip every reference encoding through clang and compare to ours.

Requires clang on PATH. On macOS clang is the system assembler; on other
hosts the script will use ``--target=arm64-apple-darwin`` to cross-compile.

Run from the repo root:

    uv run python scripts/verify_jit_encodings.py

Exits 0 if every reference entry round-trips. Exits 1 with a per-entry
report otherwise.
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from _jit_reference_data import REFERENCE_ENCODINGS  # noqa: E402


_MH_MAGIC_64 = 0xFEEDFACF
_LC_SEGMENT_64 = 0x19


def clang_arch_flags() -> list[str]:
    if sys.platform == "darwin":
        return ["-arch", "arm64"]
    return ["--target=arm64-apple-darwin"]


def assemble_one(mnemonic: str) -> bytes:
    with tempfile.TemporaryDirectory() as workdir:
        src = Path(workdir) / "in.s"
        obj = Path(workdir) / "out.o"
        src.write_text(f".section __TEXT,__text\n{mnemonic}\n")
        proc = subprocess.run(
            ["clang", *clang_arch_flags(), "-c", str(src), "-o", str(obj)],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise AssembleError(proc.stderr.decode().strip() or "clang failed")
        return extract_text_section(obj.read_bytes())


def extract_text_section(macho: bytes) -> bytes:
    magic = struct.unpack_from("<I", macho, 0)[0]
    if magic != _MH_MAGIC_64:
        raise AssembleError(f"unexpected Mach-O magic {magic:#x}")
    ncmds = struct.unpack_from("<I", macho, 16)[0]
    pos = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", macho, pos)
        if cmd == _LC_SEGMENT_64:
            section = find_text_in_segment(macho, pos)
            if section is not None:
                return section
        pos += cmdsize
    raise AssembleError("__TEXT,__text not found")


def find_text_in_segment(macho: bytes, segment_pos: int) -> bytes | None:
    nsects = struct.unpack_from("<I", macho, segment_pos + 64)[0]
    sect_pos = segment_pos + 72
    for _ in range(nsects):
        sectname = macho[sect_pos:sect_pos + 16].rstrip(b"\0")
        segname = macho[sect_pos + 16:sect_pos + 32].rstrip(b"\0")
        if segname == b"__TEXT" and sectname == b"__text":
            size = struct.unpack_from("<Q", macho, sect_pos + 40)[0]
            offset = struct.unpack_from("<I", macho, sect_pos + 48)[0]
            return macho[offset:offset + size]
        sect_pos += 80
    return None


class AssembleError(RuntimeError):
    pass


def first_word_le(buf: bytes) -> int:
    if len(buf) < 4:
        raise AssembleError(f"text section too small: {len(buf)} bytes")
    return struct.unpack_from("<I", buf, 0)[0]


def verify_all() -> tuple[list[str], list[str]]:
    matches: list[str] = []
    mismatches: list[str] = []
    for mnemonic, expected in REFERENCE_ENCODINGS:
        try:
            actual = first_word_le(assemble_one(mnemonic))
        except AssembleError as exc:
            mismatches.append(f"  ASSEMBLE FAIL  {mnemonic!r}: {exc}")
            continue
        if actual == expected:
            matches.append(f"  OK  {mnemonic:<40s}  {expected:#010x}")
        else:
            mismatches.append(
                f"  MISMATCH       {mnemonic!r}: "
                f"clang={actual:#010x} ours={expected:#010x}"
            )
    return matches, mismatches


def main() -> int:
    matches, mismatches = verify_all()
    print(f"verified {len(matches)}/{len(REFERENCE_ENCODINGS)} encodings against clang")
    if mismatches:
        print("\nFAILURES:")
        for line in mismatches:
            print(line)
        return 1
    print("all encodings round-trip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
