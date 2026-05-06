"""JIT backend.

macOS arm64 only. Requires the `com.apple.security.cs.allow-jit`
entitlement on the host Python binary; without it `mmap(MAP_JIT)` returns
MAP_FAILED and `JitRegion()` raises OSError. See README's JIT section
for the one-time codesign step.
"""
