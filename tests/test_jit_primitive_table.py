import sys
from pathlib import Path
from typing import Callable

import pytest

from mzt.jit.primitive_table import (
    PrimitiveLookupError,
    PrimitiveTable,
    load_primitives_from_dylib,
)
from mzt.primitives import all_primitives


def _expected_label_set() -> set[str]:
    return {p.label for p in all_primitives() if not p.inline}


@pytest.fixture
def fake_addresses() -> dict[str, int]:
    return {p.name: 0x1000_0000 + 16 * i for i, p in enumerate(all_primitives()) if not p.inline}


def test_address_returns_value_for_known_name(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    name = next(iter(fake_addresses))
    assert table.address(name) == fake_addresses[name], \
        "address should round-trip the value supplied to the constructor"


def test_address_raises_for_unknown_name(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    with pytest.raises(PrimitiveLookupError, match="bogus"):
        table.address("bogus")


def test_has_returns_true_for_known_name(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    name = next(iter(fake_addresses))
    assert table.has(name), "has(name) should be True for any name passed in"


def test_has_returns_false_for_unknown_name(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    assert not table.has("definitely-not-a-primitive"), \
        "has(name) should be False for names absent from the table"


def test_has_returns_false_for_inline_primitive(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    assert not table.has("zero"), \
        "inline primitives have no resolvable address; the table should reflect that"


def test_names_returns_all_passed_names(fake_addresses):
    table = PrimitiveTable(fake_addresses)
    assert set(table.names()) == set(fake_addresses), \
        "names() should report exactly what the table holds"


def test_constructor_copies_input_dict(fake_addresses):
    original = dict(fake_addresses)
    table = PrimitiveTable(fake_addresses)
    fake_addresses.clear()
    assert set(table.names()) == set(original), \
        "the table must hold an independent copy so caller mutations do not leak in"


def test_constructor_rejects_zero_address():
    with pytest.raises(PrimitiveLookupError, match="dup"):
        PrimitiveTable({"dup": 0})


def test_resolve_symbol_strips_leading_underscore_for_dlsym(mocker):
    from mzt.jit import primitive_table

    fake_lib = mocker.Mock()
    fake_func = mocker.Mock()
    fake_lib.dup = fake_func
    mocker.patch.object(primitive_table.ctypes, "cast", return_value=mocker.Mock(value=0xCAFE))

    addr = primitive_table._resolve_symbol(fake_lib, "_dup")

    assert addr == 0xCAFE, \
        "should return the cast.value when getattr succeeds"
    assert not hasattr(fake_lib, "_dup") or fake_lib.dup is fake_func, \
        "must call getattr with the underscore stripped (dlsym re-prepends _ on macOS)"


def test_resolve_symbol_with_label_lacking_underscore_passes_name_through(mocker):
    from mzt.jit import primitive_table

    fake_lib = mocker.Mock()
    fake_lib.foo = mocker.Mock()
    mocker.patch.object(primitive_table.ctypes, "cast", return_value=mocker.Mock(value=0xBEEF))

    addr = primitive_table._resolve_symbol(fake_lib, "foo")
    assert addr == 0xBEEF, "labels without leading _ should be looked up verbatim"


def test_load_from_dylib_calls_dlsym_only_once_per_label(mocker):
    fake_lib = mocker.Mock()
    addresses = {p.label: 0x2000_0000 + 16 * i for i, p in enumerate(all_primitives()) if not p.inline}
    addresses["_print_str"] = 0x2000_FFFF

    def lookup(_lib, label: str) -> int:
        return addresses[label]

    cdll = mocker.patch("mzt.jit.primitive_table.ctypes.CDLL", return_value=fake_lib)
    resolve = mocker.patch(
        "mzt.jit.primitive_table._resolve_symbol",
        side_effect=lookup,
    )

    table = load_primitives_from_dylib(Path("/fake/lib.dylib"))

    assert cdll.call_count == 1, \
        "ctypes.CDLL should only be called once when building the table"

    expected_labels = _expected_label_set()
    looked_up = {call.args[1] for call in resolve.call_args_list}
    assert expected_labels.issubset(looked_up), \
        "every non-inline primitive label should be resolved at table-build time"

    name = next(p.name for p in all_primitives() if not p.inline)
    label = next(p.label for p in all_primitives() if p.name == name)
    table.address(name)
    table.address(name)
    later_calls_for_label = [
        call for call in resolve.call_args_list if call.args[1] == label
    ]
    assert len(later_calls_for_label) == 1, \
        "after build, table.address must not re-call dlsym; lookups should be cached"


def test_load_from_dylib_raises_when_symbol_missing(mocker):
    fake_lib = mocker.Mock()
    mocker.patch("mzt.jit.primitive_table.ctypes.CDLL", return_value=fake_lib)
    mocker.patch(
        "mzt.jit.primitive_table._resolve_symbol",
        side_effect=AttributeError("symbol not exported"),
    )
    with pytest.raises(PrimitiveLookupError, match="symbol"):
        load_primitives_from_dylib(Path("/fake/lib.dylib"))


def test_load_from_dylib_raises_when_dlsym_returns_zero(mocker):
    fake_lib = mocker.Mock()
    mocker.patch("mzt.jit.primitive_table.ctypes.CDLL", return_value=fake_lib)
    mocker.patch("mzt.jit.primitive_table._resolve_symbol", return_value=0)
    with pytest.raises(PrimitiveLookupError, match="0|null"):
        load_primitives_from_dylib(Path("/fake/lib.dylib"))


@pytest.fixture(scope="module")
def real_dylib(tmp_path_factory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("dylib build needs clang and macOS")
    from mzt.jit.host_lib import build_host_library

    out = tmp_path_factory.mktemp("jit_lib") / "libmzt_host.dylib"
    return build_host_library(out)


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="dylib build needs clang and macOS"
)
def test_real_dylib_resolves_every_non_inline_primitive(real_dylib: Path):
    table = load_primitives_from_dylib(real_dylib)
    for primitive in all_primitives():
        if primitive.inline:
            continue
        addr = table.address(primitive.name)
        assert addr > 0, \
            f"{primitive.name!r} should resolve to a non-zero address in the host dylib"


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="dylib build needs clang and macOS"
)
def test_real_dylib_addresses_are_instruction_aligned(real_dylib: Path):
    table = load_primitives_from_dylib(real_dylib)
    for primitive in all_primitives():
        if primitive.inline:
            continue
        addr = table.address(primitive.name)
        assert addr % 4 == 0, \
            f"{primitive.name!r} address {addr:#x} must be 4-byte aligned per ARM64 ABI"


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="dylib build needs clang and macOS"
)
def test_real_dylib_distinct_primitives_have_distinct_addresses(real_dylib: Path):
    table = load_primitives_from_dylib(real_dylib)
    seen: dict[int, str] = {}
    for primitive in all_primitives():
        if primitive.inline:
            continue
        addr = table.address(primitive.name)
        assert addr not in seen, \
            f"{primitive.name!r} resolves to the same address as {seen.get(addr)!r}: {addr:#x}"
        seen[addr] = primitive.name
