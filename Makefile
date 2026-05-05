FS_EXAMPLES := $(patsubst %.fs,%,$(wildcard examples/*.fs))

.PHONY: test examples clean

test:
	uv run pytest

examples: examples/hello $(FS_EXAMPLES)

examples/hello: examples/hello.s
	uv run python -c "from pathlib import Path; from mzt.builder import build; build(Path('examples/hello.s').read_text(), Path('examples/hello'))"

examples/%: examples/%.fs
	uv run mzt build $< -o $@

clean:
	rm -rf .pytest_cache build dist *.egg-info
	rm -f examples/hello $(FS_EXAMPLES)
	rm -f examples/*.s
	@# keep the hand-written reference
	git checkout -- examples/hello.s 2>/dev/null || true
	find . -name __pycache__ -type d -exec rm -rf {} +
