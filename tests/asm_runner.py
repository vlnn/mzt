import struct
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


_MH_MAGIC_64 = 0xFEEDFACF
_LC_SEGMENT_64 = 0x19


def _clang_arch_flags() -> list[str]:
    if sys.platform == "darwin":
        return ["-arch", "arm64"]
    return ["--target=arm64-apple-darwin"]


def _detect_harness() -> tuple[bool, str | None]:
    try:
        import unicorn  # noqa: F401
    except ImportError as exc:
        return False, f"unicorn not importable: {exc!r}"

    src_path = obj_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".s", mode="w", delete=False) as src:
            src.write(".section __TEXT,__text\nret\n")
            src_path = src.name
        with tempfile.NamedTemporaryFile(suffix=".o", delete=False) as obj:
            obj_path = obj.name
        proc = subprocess.run(
            ["clang", *_clang_arch_flags(), "-c", src_path, "-o", obj_path],
            capture_output=True,
        )
        if proc.returncode != 0:
            return False, f"clang cannot produce arm64 Mach-O: {proc.stderr.decode().strip()!r}"
        if Path(obj_path).read_bytes()[:4] != b"\xcf\xfa\xed\xfe":
            return False, "clang did not produce a 64-bit little-endian Mach-O object"
    except FileNotFoundError as exc:
        return False, f"clang not on PATH: {exc!r}"
    finally:
        for path in (src_path, obj_path):
            if path is not None:
                Path(path).unlink(missing_ok=True)

    return True, None


HARNESS_AVAILABLE, HARNESS_ERROR = _detect_harness()


if HARNESS_AVAILABLE:
    import unicorn
    from unicorn.arm64_const import UC_ARM64_REG_X19


CODE_BASE = 0x1000_0000
STACK_BASE = 0x2000_0000
STACK_SIZE = 4096


class HarnessUnavailable(RuntimeError):
    pass


class StackUnderflow(RuntimeError):
    pass


class AssemblerError(RuntimeError):
    pass


def _require_harness() -> None:
    if not HARNESS_AVAILABLE:
        raise HarnessUnavailable(f"primitive harness unavailable: {HARNESS_ERROR}")


@lru_cache(maxsize=None)
def assemble(asm_text: str) -> bytes:
    _require_harness()
    with tempfile.TemporaryDirectory() as workdir:
        src = Path(workdir) / "in.s"
        obj = Path(workdir) / "out.o"
        src.write_text(".section __TEXT,__text\n" + asm_text)
        proc = subprocess.run(
            ["clang", *_clang_arch_flags(), "-c", str(src), "-o", str(obj)],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise AssemblerError(proc.stderr.decode().strip())
        return _extract_text_section(obj.read_bytes())


def _extract_text_section(macho: bytes) -> bytes:
    magic = struct.unpack_from("<I", macho, 0)[0]
    if magic != _MH_MAGIC_64:
        raise AssemblerError(f"unexpected Mach-O magic {magic:#x}")
    ncmds = struct.unpack_from("<I", macho, 16)[0]
    pos = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", macho, pos)
        if cmd == _LC_SEGMENT_64:
            section_bytes = _find_text_in_segment(macho, pos)
            if section_bytes is not None:
                return section_bytes
        pos += cmdsize
    raise AssemblerError("__TEXT,__text section not found in Mach-O object")


def _find_text_in_segment(macho: bytes, segment_pos: int) -> bytes | None:
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


def run_primitive(asm_body: str, stack_in: list[int]) -> list[int]:
    _require_harness()
    code = assemble(asm_body + "\n")
    uc = _make_emulator(code)
    initial_x19 = _load_initial_stack(uc, stack_in)
    uc.reg_write(UC_ARM64_REG_X19, initial_x19)
    uc.emu_start(CODE_BASE, CODE_BASE + len(code))
    return _read_stack(uc, uc.reg_read(UC_ARM64_REG_X19))


def _make_emulator(code: bytes):
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(CODE_BASE, 4096)
    uc.mem_map(STACK_BASE, STACK_SIZE)
    uc.mem_write(CODE_BASE, code)
    return uc


def _load_initial_stack(uc, stack_in: list[int]) -> int:
    stack_top = STACK_BASE + STACK_SIZE
    initial_x19 = stack_top - 8 * len(stack_in)
    for offset, value in enumerate(reversed(stack_in)):
        uc.mem_write(initial_x19 + 8 * offset, _to_bytes(value))
    return initial_x19


def _read_stack(uc, x19: int) -> list[int]:
    stack_top = STACK_BASE + STACK_SIZE
    if x19 > stack_top:
        raise StackUnderflow(
            f"primitive popped past the bottom of the stack (x19=0x{x19:x})"
        )
    cells: list[int] = []
    for addr in range(stack_top - 8, x19 - 1, -8):
        cells.append(int.from_bytes(uc.mem_read(addr, 8), "little", signed=True))
    return cells


def _to_bytes(value: int) -> bytes:
    masked = value & 0xFFFFFFFFFFFFFFFF
    return masked.to_bytes(8, "little", signed=False)
