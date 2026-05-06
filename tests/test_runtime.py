import pytest

from mzt.runtime import RSTACK_BYTES, runtime_epilogue, runtime_preamble


def test_preamble_initializes_data_stack_pointer_x19():
    asm = runtime_preamble()
    assert "adrp    x19, Ldstack_base@PAGE" in asm, \
        "preamble should load address of Ldstack_base into x19 (data-stack base)"


def test_preamble_initializes_return_stack_pointer_x20():
    asm = runtime_preamble()
    assert "adrp    x20, Lrstack_base@PAGE" in asm, \
        "preamble should load address of Lrstack_base into x20 (return-stack base)"


def test_preamble_grows_return_stack_pointer_to_top():
    asm = runtime_preamble()
    assert f"add     x20, x20, #{RSTACK_BYTES}" in asm, \
        "preamble should advance x20 to the top of Lrstack_base since the return stack grows down"


def test_epilogue_reserves_zerofill_block_for_return_stack():
    asm = runtime_epilogue(user_memory_bytes=0)
    assert ".zerofill __DATA,__bss,Lrstack_base," in asm, \
        "epilogue should reserve a zerofill block named Lrstack_base in the BSS"


@pytest.mark.parametrize("user_memory_bytes", [0, 16, 64, 1024])
def test_return_stack_block_size_is_fixed(user_memory_bytes):
    asm = runtime_epilogue(user_memory_bytes=user_memory_bytes)
    assert f"Lrstack_base,{RSTACK_BYTES}," in asm, \
        f"return-stack reservation should be {RSTACK_BYTES} bytes regardless of user memory size"


def test_x20_is_initialized_after_x19():
    asm = runtime_preamble()
    x19_init = asm.index("adrp    x19, Ldstack_base@PAGE")
    x20_init = asm.index("adrp    x20, Lrstack_base@PAGE")
    bl_main = asm.index("bl      _word_main")
    assert x19_init < x20_init < bl_main, \
        "both stack pointers must be initialized before main is called"


def test_rstack_bytes_constant_is_at_least_4kb():
    assert RSTACK_BYTES >= 4096, \
        f"return stack must be at least one page; got {RSTACK_BYTES} bytes"
