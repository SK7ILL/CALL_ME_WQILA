install:
	uv sync

run:
	uv run -m src

debug:
	python -m pdb -m src

clean:
	rm -rf __pycache__
	rm -rf .mypy_cache

lint:
	uv run python3 -m flake8 --exclude=.venv .
	uv run python3 -m mypy --exclude=.venv --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .
