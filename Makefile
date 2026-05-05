.PHONY: test examples clean

test:
	uv run pytest

examples: examples/hello

examples/hello: examples/hello.s
	uv run python -c "from pathlib import Path; from mzt.builder import build; build(Path('examples/hello.s').read_text(), Path('examples/hello'))"

clean:
	rm -rf .pytest_cache build dist *.egg-info
	rm -f examples/hello
	find . -name __pycache__ -type d -exec rm -rf {} +
