import ctypes
import platform
import sys
from ctypes import util as ctypes_util


PROT_READ = 0x1
PROT_WRITE = 0x2
PROT_EXEC = 0x4

MAP_PRIVATE = 0x0002
MAP_ANON_DARWIN = 0x1000
MAP_JIT_DARWIN = 0x0800

MAP_FAILED = -1


def is_supported_platform() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"


def unsupported_reason() -> str:
    if sys.platform != "darwin":
        return f"JIT requires macOS; running on {sys.platform!r}"
    if platform.machine() != "arm64":
        return f"JIT requires Apple Silicon; running on {platform.machine()!r}"
    return ""


class JitAllocationError(OSError):
    pass


class Libc:
    def __init__(self, libc, libsystem_pthread):
        self._libc = libc
        self._pthread = libsystem_pthread
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        self._libc.mmap.restype = ctypes.c_void_p
        self._libc.mmap.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_long,
        ]
        self._libc.munmap.restype = ctypes.c_int
        self._libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        self._libc.sys_icache_invalidate.restype = None
        self._libc.sys_icache_invalidate.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
        ]
        self._pthread.pthread_jit_write_protect_np.restype = None
        self._pthread.pthread_jit_write_protect_np.argtypes = [ctypes.c_int]

    def allocate_jit(self, size: int) -> int:
        flags = MAP_PRIVATE | MAP_ANON_DARWIN | MAP_JIT_DARWIN
        addr = self._libc.mmap(
            None, size, PROT_READ | PROT_WRITE | PROT_EXEC, flags, -1, 0,
        )
        if addr in (None, 0) or addr == ctypes.c_void_p(MAP_FAILED).value:
            raise JitAllocationError(
                f"mmap(MAP_JIT) failed for size={size}; "
                "is com.apple.security.cs.allow-jit set on the host binary?"
            )
        return int(addr)

    def deallocate(self, base: int, size: int) -> None:
        self._libc.munmap(ctypes.c_void_p(base), size)

    def set_writable(self, writable: bool) -> None:
        self._pthread.pthread_jit_write_protect_np(0 if writable else 1)

    def flush_icache(self, base: int, size: int) -> None:
        self._libc.sys_icache_invalidate(ctypes.c_void_p(base), size)


def load_system_libc() -> Libc:
    if not is_supported_platform():
        raise RuntimeError(unsupported_reason())
    libc_path = ctypes_util.find_library("c") or "libc.dylib"
    pthread_path = ctypes_util.find_library("pthread") or "libsystem_pthread.dylib"
    return Libc(ctypes.CDLL(libc_path), ctypes.CDLL(pthread_path))
