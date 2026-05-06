FS_EXAMPLES := $(patsubst %.fs,%,$(wildcard examples/*.fs))
FORTH_TESTS := $(wildcard tests/forth/test_*.fs)

.PHONY: test forth-test examples bench clean

test:
	uv run pytest

# Run only the Forth-side tests. Each `: test-*` colon definition in
# tests/forth/test_*.fs becomes one pytest item via conftest.py.
# Adding a new test = drop a test_*.fs file in tests/forth/.
forth-test:
	uv run pytest tests/forth/ -v

examples: examples/hello $(FS_EXAMPLES)

examples/hello: examples/hello.s
	uv run python -c "from pathlib import Path; from mzt.builder import build; build(Path('examples/hello.s').read_text(), Path('examples/hello'))"

examples/%: examples/%.fs
	uv run mzt build $< -o $@

# Build and time the benchmark binaries. Expected outputs are part of
# the source comments; the deterministic values are also locked in by
# tests/forth/test_benchmarks.fs (smaller inputs, run via pytest).
bench: examples/bench-fib examples/bench-pi
	@echo "=== bench-fib (expect: 9227465) ==="
	@time ./examples/bench-fib
	@echo
	@echo "=== bench-pi  (expect: 31416020) ==="
	@time ./examples/bench-pi

clean:
	rm -rf .pytest_cache build dist *.egg-info
	rm -f examples/hello $(FS_EXAMPLES)
	rm -f examples/*.s
	@# keep the hand-written reference
	git checkout -- examples/hello.s 2>/dev/null || true
	find . -name __pycache__ -type d -exec rm -rf {} +
