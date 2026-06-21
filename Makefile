.PHONY: install test lint format build clean demo

install:
	pip install -e ".[dev]"

install-web:
	pip install -e ".[all]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=open_migration --cov-report=term-missing --cov-report=html

lint:
	ruff check open_migration/ tests/

format:
	ruff format open_migration/ tests/

typecheck:
	mypy open_migration/

build:
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info/ htmlcov/ .coverage .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run a quick demo with the sample data
demo:
	omigrate convert \
		--input examples/sample_chatgpt.json \
		--source chatgpt \
		--target html \
		--output /tmp/omigrate-demo \
		--open

demo-obsidian:
	omigrate convert \
		--input examples/sample_claude.json \
		--source claude \
		--target obsidian \
		--output /tmp/omigrate-demo-vault

demo-merge:
	omigrate merge \
		--inputs examples/sample_chatgpt.json examples/sample_claude.json \
		--target html \
		--output /tmp/omigrate-demo-merged

serve:
	omigrate serve

release-check: clean lint test build
	@echo "✓ Release checks passed"
