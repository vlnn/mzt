from mzt.builder import compile_to_asm


def _trivial_program_asm() -> str:
    return compile_to_asm(": main 1 . ;")


def test_main_calls_setbuf_to_disable_stdout_buffering():
    asm = _trivial_program_asm()
    assert "_setbuf" in asm, \
        "main must call setbuf so user printf output and unbuffered _write " \
        "output appear in source order — without this, the REPL state-dump " \
        "markers arrive before user output and parse_state_dump strips it"


def test_setbuf_uses_macos_stdout_pointer_symbol():
    asm = _trivial_program_asm()
    assert "___stdoutp" in asm, \
        "setbuf must reference macOS's __stdoutp pointer (mangled as ___stdoutp); " \
        "anything else won't link against libSystem"


def test_setbuf_call_precedes_word_main_invocation():
    asm = _trivial_program_asm()
    setbuf_idx = asm.find("bl      _setbuf")
    main_call_idx = asm.find("bl      _word_main")
    assert setbuf_idx > -1, "the setbuf call must be present"
    assert main_call_idx > -1, "the _word_main call must be present"
    assert setbuf_idx < main_call_idx, \
        "setbuf must run before user code so all subsequent printf calls are unbuffered"


def test_setbuf_call_passes_null_buffer():
    asm = _trivial_program_asm()
    setbuf_block = asm[asm.find("___stdoutp"):asm.find("bl      _setbuf")]
    assert "mov     x1, #0" in setbuf_block, \
        "setbuf's second argument (buf) must be NULL to request unbuffered mode"
