import re
import sys

import pytest

from mzt.primitives import all_primitives, is_primitive, primitive


def test_dispatch_main_is_registered_as_a_primitive():
    assert is_primitive("dispatch-main"), \
        "dispatch-main should be registered alongside the other primitives"


def test_dispatch_main_label_is_dispatch_main():
    assert primitive("dispatch-main").label == "_dispatch_main", \
        "the asm label for dispatch-main should be the conventional underscored form"


def test_dispatch_main_is_not_inline():
    assert not primitive("dispatch-main").inline, \
        "dispatch-main is too big to inline — it must be called via blr like other primitives"


def test_dispatch_main_body_pops_fn_address_into_x0():
    body = primitive("dispatch-main").body
    assert "ldr     x0, [x19], #8" in body or "ldr x0, [x19], #8" in body, \
        "dispatch-main must pop the function address from the data stack into x0"


def test_dispatch_main_body_calls_the_dispatch_helper():
    body = primitive("dispatch-main").body
    assert "bl      _mzt_dispatch_main" in body or "bl _mzt_dispatch_main" in body, \
        "dispatch-main primitive should delegate to the host's _mzt_dispatch_main helper"


def test_dispatch_main_body_brackets_the_call_in_a_frame():
    body = primitive("dispatch-main").body
    assert "stp     x29, x30, [sp, #-16]!" in body or "stp x29, x30, [sp, #-16]!" in body, \
        "dispatch-main makes a bl call, so it must save x30 in a frame"
    assert "ldp     x29, x30, [sp], #16" in body or "ldp x29, x30, [sp], #16" in body, \
        "dispatch-main must restore x29/x30 after the bl call returns"


def test_dispatch_main_is_marked_jit_only():
    assert primitive("dispatch-main").jit_only, \
        "dispatch-main bodies the bl _mzt_dispatch_main; that symbol only exists in the JIT host lib"


def test_other_primitives_are_not_jit_only():
    for p in all_primitives():
        if p.name == "dispatch-main":
            continue
        assert not p.jit_only, \
            f"{p.name!r} is not JIT-specific; it should be available in the AOT runtime too"


def test_runtime_preamble_excludes_jit_only_bodies():
    from mzt.runtime import runtime_preamble
    asm = runtime_preamble()
    assert "_dispatch_main:" not in asm, \
        "the AOT runtime preamble must not emit the body of a JIT-only primitive — clang would reject the unresolved bl _mzt_dispatch_main"
    assert "_mzt_dispatch_main" not in asm, \
        "the AOT runtime should not even reference _mzt_dispatch_main"


def test_runtime_preamble_still_emits_normal_primitives():
    from mzt.runtime import runtime_preamble
    asm = runtime_preamble()
    for label in ("_dup", "_drop", "_plus", "_minus", "_dot"):
        assert f"{label}:" in asm, \
            f"AOT preamble must still emit the body of normal primitive {label!r}; the jit_only filter only skips dispatch-main"


def test_aot_emitter_raises_for_jit_only_primitive():
    from mzt.emitter import EmitError, emit_program
    from mzt.ir import ColonDef, PrimRef
    body = (PrimRef("dispatch-main"),)
    main_def = ColonDef(name="main", body=body, source_text=": main dispatch-main ;")
    with pytest.raises(EmitError, match="dispatch-main"):
        emit_program([main_def])


def test_all_primitives_includes_dispatch_main():
    names = [p.name for p in all_primitives()]
    assert "dispatch-main" in names, \
        "all_primitives() must enumerate dispatch-main so the host_lib emits its body"


def test_dispatch_main_is_idiomatic_forth_name():
    assert "-" in "dispatch-main", \
        "Forth idiom uses hyphens; the primitive name must follow that convention"


def test_host_library_asm_globalises_dispatch_helpers():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert ".globl _mzt_dispatch_main" in asm, \
        "_mzt_dispatch_main must be exported so the dispatch-main primitive can bl into it"
    assert ".globl _invoke_with_stacks" in asm, \
        "_invoke_with_stacks must be exported so libdispatch can be told to call it"


def test_host_library_asm_defines_dispatch_helper_labels():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert re.search(r"^_mzt_dispatch_main:", asm, re.MULTILINE), \
        "_mzt_dispatch_main: label must be defined to back the .globl"
    assert re.search(r"^_invoke_with_stacks:", asm, re.MULTILINE), \
        "_invoke_with_stacks: label must be defined as the dispatch trampoline"


def test_host_library_asm_includes_dispatch_dstack_zerofill():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert ".zerofill __DATA,__bss,Ldispatch_dstack" in asm, \
        "dispatched code needs its own dstack memory; it cannot share the REPL's Ldstack_base"


def test_host_library_asm_includes_dispatch_rstack_zerofill():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert ".zerofill __DATA,__bss,Ldispatch_rstack" in asm, \
        "dispatched code needs its own rstack memory"


def test_invoke_with_stacks_calls_the_main_trampoline():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    invoke_section = asm.split("_invoke_with_stacks:", 1)[1].split("\n_", 1)[0]
    assert "bl      _trampoline" in invoke_section or "bl _trampoline" in invoke_section, \
        "_invoke_with_stacks reuses the main _trampoline so dispatched fns get proper x19/x20"


def test_mzt_dispatch_main_calls_libdispatch():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    section = asm.split("_mzt_dispatch_main:", 1)[1].split("\n_", 1)[0]
    assert "bl      _dispatch_async_f" in section or "bl _dispatch_async_f" in section, \
        "_mzt_dispatch_main must hand off to libdispatch's dispatch_async_f"


def test_mzt_dispatch_main_does_not_use_gotpage_for_main_queue():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert "@GOTPAGE" not in asm, \
        "_dispatch_main_q@GOTPAGE forces the linker to bind the GOT entry at dlopen time, which fails on modern macOS — use a same-image data slot populated by Python instead"


def test_host_library_asm_exports_mzt_main_q():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert ".globl _mzt_main_q" in asm, \
        "_mzt_main_q must be exported so Python can write the queue address to it via in_dll"


def test_host_library_asm_defines_mzt_main_q_data_slot():
    import re
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    assert ".section __DATA,__data" in asm, \
        "_mzt_main_q lives in __DATA,__data so Python can write to it after dlopen"
    assert re.search(r"^_mzt_main_q:", asm, re.MULTILINE), \
        "_mzt_main_q label must be defined in the data section as the Python-populated queue pointer"


def test_mzt_dispatch_main_loads_queue_from_mzt_main_q():
    from mzt.jit.host_lib import emit_host_library_asm
    asm = emit_host_library_asm()
    section = asm.split("_mzt_dispatch_main:", 1)[1].split("\n_", 1)[0]
    assert "_mzt_main_q@PAGE" in section, \
        "_mzt_dispatch_main must read the queue handle from the same-image _mzt_main_q slot"
    assert "_dispatch_main_q" not in section, \
        "_mzt_dispatch_main must NOT reference _dispatch_main_q directly — that's what was failing dlopen"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_built_dylib_exports_dispatch_main(tmp_path):
    import ctypes
    from mzt.jit.host_lib import build_host_library

    out = tmp_path / "libmzt_host.dylib"
    build_host_library(out)
    lib = ctypes.CDLL(str(out))
    assert lib.dispatch_main is not None, \
        "ctypes should resolve _dispatch_main via dlsym (underscore stripped per macOS convention)"


@pytest.mark.skipif(sys.platform != "darwin", reason="dylib build needs clang and macOS")
def test_built_dylib_exports_mzt_dispatch_main(tmp_path):
    import ctypes
    from mzt.jit.host_lib import build_host_library

    out = tmp_path / "libmzt_host.dylib"
    build_host_library(out)
    lib = ctypes.CDLL(str(out))
    assert lib.mzt_dispatch_main is not None, \
        "the C-level dispatch helper must be resolvable so the primitive can bl into it"


@pytest.mark.skipif(sys.platform != "darwin", reason="needs real JIT host")
def test_dispatch_main_resolves_through_primitive_table(tmp_path):
    from mzt.jit.host_lib import build_host_library
    from mzt.jit.primitive_table import load_primitives_from_dylib

    out = tmp_path / "libmzt_host.dylib"
    build_host_library(out)
    table = load_primitives_from_dylib(out)
    addr = table.address("dispatch-main")
    assert addr > 0 and addr % 4 == 0, \
        f"dispatch-main must resolve to a non-null, instruction-aligned address; got {addr:#x}"


class _FakeLib:
    pass


def test_populate_writes_resolved_handle_into_mzt_main_q(mocker):
    import ctypes
    from mzt.jit import executor as executor_mod

    fake_lib = _FakeLib()
    storage = ctypes.c_uint64(0)
    mocker.patch.object(executor_mod, "_resolve_main_queue_handle", return_value=0xCAFE_BABE)
    mocker.patch.object(ctypes.c_uint64, "in_dll", return_value=storage)

    executor_mod._populate_main_queue_pointer(fake_lib)

    assert storage.value == 0xCAFE_BABE, \
        "the populate helper should copy whatever _resolve_main_queue_handle returns into _mzt_main_q"


def test_resolve_main_queue_prefers_dispatch_get_main_queue_function(mocker):
    from mzt.jit import executor as executor_mod

    runtime = mocker.MagicMock()
    runtime.dispatch_get_main_queue.return_value = 0xCAFE
    mocker.patch.object(executor_mod.ctypes, "CDLL", return_value=runtime)

    handle = executor_mod._resolve_main_queue_handle()

    assert handle == 0xCAFE, \
        "when libdispatch exposes dispatch_get_main_queue() as a callable, that should be the first source consulted"


def test_resolve_main_queue_falls_back_to_data_symbol_when_function_missing(mocker):
    import ctypes
    from mzt.jit import executor as executor_mod

    runtime = mocker.MagicMock(spec=[])
    mocker.patch.object(executor_mod.ctypes, "CDLL", return_value=runtime)

    sentinel = ctypes.c_long(0)
    mocker.patch.object(ctypes.c_long, "in_dll", return_value=sentinel)

    handle = executor_mod._resolve_main_queue_handle()

    assert handle == ctypes.addressof(sentinel), \
        "if the function isn't exported (older macOS or stripped), the data-symbol path should provide the queue handle"


def test_resolve_main_queue_returns_zero_when_no_strategy_works(mocker):
    import ctypes
    from mzt.jit import executor as executor_mod

    runtime = mocker.MagicMock(spec=[])
    mocker.patch.object(executor_mod.ctypes, "CDLL", return_value=runtime)
    mocker.patch.object(ctypes.c_long, "in_dll", side_effect=ValueError("symbol not found"))

    handle = executor_mod._resolve_main_queue_handle()

    assert handle == 0, \
        "if neither lookup works, _resolve_main_queue_handle returns 0 — _mzt_main_q stays null and dispatch-main is a no-op until Step 8 wires up a real runloop"


def test_ensure_host_library_skips_rebuild_when_asm_matches(tmp_path, mocker):
    from mzt.jit import executor as executor_mod

    dylib = tmp_path / "libmzt_host.dylib"
    asm_path = tmp_path / "libmzt_host.s"
    expected_asm = "FAKE-ASM-CONTENT"
    dylib.write_bytes(b"any-content")
    asm_path.write_text(expected_asm)

    mocker.patch.object(executor_mod, "emit_host_library_asm", return_value=expected_asm)
    build = mocker.patch.object(executor_mod, "build_host_library")

    executor_mod._ensure_host_library(dylib)

    build.assert_not_called(), \
        "when the cached .s file matches the freshly-generated asm, the dylib should be reused without invoking clang"


def test_ensure_host_library_rebuilds_when_asm_differs(tmp_path, mocker):
    from mzt.jit import executor as executor_mod

    dylib = tmp_path / "libmzt_host.dylib"
    asm_path = tmp_path / "libmzt_host.s"
    dylib.write_bytes(b"stale-content")
    asm_path.write_text("STALE-ASM")

    mocker.patch.object(executor_mod, "emit_host_library_asm", return_value="FRESH-ASM")
    build = mocker.patch.object(executor_mod, "build_host_library")

    executor_mod._ensure_host_library(dylib)

    build.assert_called_once_with(dylib, asm="FRESH-ASM"), \
        "when the cached .s drifts from the freshly-generated asm, the dylib must be rebuilt to pick up the change"


def test_ensure_host_library_rebuilds_when_dylib_missing(tmp_path, mocker):
    from mzt.jit import executor as executor_mod

    dylib = tmp_path / "libmzt_host.dylib"
    mocker.patch.object(executor_mod, "emit_host_library_asm", return_value="ASM")
    build = mocker.patch.object(executor_mod, "build_host_library")

    executor_mod._ensure_host_library(dylib)

    build.assert_called_once_with(dylib, asm="ASM"), \
        "first-time builds (no cached dylib at the path) must always invoke clang"


def test_ensure_host_library_rebuilds_when_asm_companion_missing(tmp_path, mocker):
    from mzt.jit import executor as executor_mod

    dylib = tmp_path / "libmzt_host.dylib"
    dylib.write_bytes(b"orphan-content")
    mocker.patch.object(executor_mod, "emit_host_library_asm", return_value="ASM")
    build = mocker.patch.object(executor_mod, "build_host_library")

    executor_mod._ensure_host_library(dylib)

    build.assert_called_once_with(dylib, asm="ASM"), \
        "without the companion .s file we cannot verify the dylib's provenance — rebuild to be safe"
