.PHONY: lint format typecheck test all

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

test:
	pytest

all: lint typecheck test
