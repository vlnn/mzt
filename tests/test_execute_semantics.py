import pytest

import asm_runner
from asm_runner import CODE_BASE, run_with_stacks


pytestmark = pytest.mark.skipif(
    not asm_runner.HARNESS_AVAILABLE,
    reason=f"primitive harness unavailable: {asm_runner.HARNESS_ERROR}",
)


def test_execute_pops_address_and_branches_to_it():
    # Layout (each instruction = 4 bytes):
    #   offset 0:  ldr x9, [x19], #8     ; _execute body — pop addr to x9
    #   offset 4:  br  x9                 ; _execute body — jump
    #   offset 8:  mov x0, #99            ; target: push 99
    #   offset 12: str x0, [x19, #-8]!    ; target: complete the push, then halt
    body = (
        "    ldr     x9, [x19], #8\n"
        "    br      x9\n"
        "    mov     x0, #99\n"
        "    str     x0, [x19, #-8]!\n"
    )
    target_addr = CODE_BASE + 8
    dstack, _ = run_with_stacks(body, dstack_in=[target_addr], rstack_in=[])
    assert dstack == [99], \
        f"execute should branch to the popped address; the target pushed 99 to dstack; got {dstack}"


def test_execute_advances_x19_consuming_the_address():
    # If execute leaves the address on the stack instead of consuming it, the
    # 99 we expect would land BELOW the stale address.
    body = (
        "    ldr     x9, [x19], #8\n"
        "    br      x9\n"
        "    mov     x0, #99\n"
        "    str     x0, [x19, #-8]!\n"
    )
    target_addr = CODE_BASE + 8
    dstack, _ = run_with_stacks(body, dstack_in=[target_addr], rstack_in=[])
    assert len(dstack) == 1 and dstack[0] == 99, \
        f"execute must consume the popped address, not leave it on the stack; got {dstack}"
