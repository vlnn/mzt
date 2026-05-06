import subprocess
import sys
from pathlib import Path

import pytest

from mzt.builder import build, build_source, compile_to_asm
from mzt.compiler import CompileError

EXAMPLES = Path(__file__).parent.parent / "examples"

apple_silicon_only = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="M0 hello binary is Mach-O arm64; only runs on Apple Silicon",
)


def test_build_writes_assembly_alongside_output(mocker, tmp_build_dir):
    mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    build(".text\n_main: ret\n", out)

    assert out.with_suffix(".s").read_text() == ".text\n_main: ret\n", \
        "build should persist the assembly text next to the output binary"


def test_build_returns_output_path(mocker, tmp_build_dir):
    mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    result = build("ignored", out)

    assert result == out, \
        "build should return the output path so callers can chain off it"


@pytest.mark.parametrize(
    "expected_token",
    ["clang", "-arch", "arm64", "-o"],
)
def test_clang_invocation_includes(mocker, tmp_build_dir, expected_token):
    run = mocker.patch("mzt.builder.subprocess.run")

    build("ignored", tmp_build_dir / "hello")

    cmd = run.call_args.args[0]
    assert expected_token in cmd, \
        f"clang invocation should include {expected_token!r}, got {cmd!r}"


def test_clang_targets_arm64_explicitly(mocker, tmp_build_dir):
    run = mocker.patch("mzt.builder.subprocess.run")

    build("ignored", tmp_build_dir / "hello")

    cmd = run.call_args.args[0]
    arch_value = cmd[cmd.index("-arch") + 1]
    assert arch_value == "arm64", \
        f"-arch flag should be followed by 'arm64', got {arch_value!r}"


def test_clang_writes_to_requested_output_path(mocker, tmp_build_dir):
    run = mocker.patch("mzt.builder.subprocess.run")
    out = tmp_build_dir / "hello"

    build("ignored", out)

    cmd = run.call_args.args[0]
    output_value = cmd[cmd.index("-o") + 1]
    assert output_value == str(out), \
        f"-o flag should be followed by the requested output path, got {output_value!r}"


def test_build_propagates_clang_failure(mocker, tmp_build_dir):
    mocker.patch(
        "mzt.builder.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, ["clang"]),
    )

    with pytest.raises(subprocess.CalledProcessError):
        build("ignored", tmp_build_dir / "hello")


@apple_silicon_only
def test_m0_hello_runs(tmp_build_dir):
    asm_text = (EXAMPLES / "hello.s").read_text()

    binary = build(asm_text, tmp_build_dir / "hello")
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True, check=True
    )

    assert result.stdout == "hello\n", \
        "M0 hand-written hello.s should print 'hello' followed by a newline"


def test_compile_to_asm_threads_source_through_pipeline():
    asm = compile_to_asm(": main 2 3 + . ;")
    for fragment in ("_word_main:", "ldr     x0, =2", "ldr     x0, =3", "bl      _plus", "bl      _dot"):
        assert fragment in asm, \
            f"compile_to_asm should produce assembly containing {fragment!r}"


def test_compile_to_asm_requires_main_word():
    with pytest.raises(CompileError, match="main"):
        compile_to_asm(": helper 1 ;")


def test_build_source_writes_assembly_for_compiled_program(mocker, tmp_build_dir, tmp_path):
    mocker.patch("mzt.builder.subprocess.run")
    src = tmp_path / "x.fs"
    src.write_text(": main 2 3 + . ;\n")
    out = tmp_build_dir / "x"

    build_source(src, out)

    asm = out.with_suffix(".s").read_text()
    assert "_word_main:" in asm, \
        "build_source should compile the source through to assembly"
    assert "ldr     x0, =2" in asm and "ldr     x0, =3" in asm, \
        "literals from the source should appear in the emitted assembly"


def test_build_source_invokes_clang(mocker, tmp_build_dir, tmp_path):
    run = mocker.patch("mzt.builder.subprocess.run")
    src = tmp_path / "x.fs"
    src.write_text(": main 0 . ;\n")

    build_source(src, tmp_build_dir / "x")

    cmd = run.call_args.args[0]
    assert cmd[0] == "clang" and "-arch" in cmd and "arm64" in cmd, \
        "build_source should still hand the assembly to clang -arch arm64"


def test_build_source_returns_output_path(mocker, tmp_build_dir, tmp_path):
    mocker.patch("mzt.builder.subprocess.run")
    src = tmp_path / "x.fs"
    src.write_text(": main 0 . ;\n")
    out = tmp_build_dir / "x"

    result = build_source(src, out)

    assert result == out, "build_source should return the output binary path"


def test_build_source_raises_when_main_missing(mocker, tmp_build_dir, tmp_path):
    run = mocker.patch("mzt.builder.subprocess.run")
    src = tmp_path / "x.fs"
    src.write_text(": helper 1 ;\n")

    with pytest.raises(CompileError, match="main"):
        build_source(src, tmp_build_dir / "x")

    run.assert_not_called()


def test_compile_to_asm_runs_zero_push_peephole():
    asm = compile_to_asm(": main 0 . ;")
    assert "ldr     x0, =0" not in asm, \
        "after peephole, Literal(0) must not survive as an ldr =0"
    assert "str     xzr, [x19, #-8]!" in asm, \
        "Literal(0) should be inlined as str xzr push"


def test_compile_to_asm_fuses_swap_drop():
    asm = compile_to_asm(": main 1 2 swap drop . ;")
    assert "bl      _swap" not in asm, "swap drop must be peepholed away"
    assert "bl      _drop" not in asm, "swap drop must be peepholed away"
    assert "bl      _nip" in asm, "swap drop must fuse to bl _nip"


def test_nonzero_literals_still_use_ldr():
    asm = compile_to_asm(": main 1 . ;")
    assert "ldr     x0, =1" in asm, \
        "non-zero literals are not affected by the zero-push rule"


def test_compile_to_asm_handles_variable_definition():
    asm = compile_to_asm("variable counter : main counter @ . ;")
    assert "_word_counter:" in asm, \
        "variable should produce a colon-style word that pushes its address"
    assert "Luser_mem" in asm, \
        "asm should reference the user-memory base for the variable's address"
    assert ".zerofill __DATA,__bss,Luser_mem" in asm, \
        "runtime should reserve user-memory bss space"


def test_compile_to_asm_handles_create_with_allot():
    asm = compile_to_asm("create buf 32 allot : main buf . ;")
    assert ".zerofill __DATA,__bss,Luser_mem,32,3" in asm, \
        "32 allot should produce a 32-byte user-memory block"


def test_compile_to_asm_user_memory_bytes_grows_with_variables():
    asm = compile_to_asm("variable a variable b variable c : main a . ;")
    assert ".zerofill __DATA,__bss,Luser_mem,32,3" in asm, \
        "three 8-byte variables = 24 bytes, rounded up to 32 (16-byte boundary)"


def test_variable_address_is_pushed_via_adrp_add():
    asm = compile_to_asm("variable counter : main counter ;")
    counter_section = asm[asm.index("_word_counter:"):asm.index("_word_main:")]
    assert "adrp    x0, Luser_mem@PAGE" in counter_section, \
        "counter's body should load user-mem base via adrp"
    assert "str     x0, [x19, #-8]!" in counter_section, \
        "counter's body should push the address onto the stack"
