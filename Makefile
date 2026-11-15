NAME = FLAME-IN-FREEFALL

all: install run

install:
	@python3 -m venv .venv
	@.venv/bin/pip install uv
	@.venv/bin/uv sync

run:
	@.venv/bin/python3 -m streamlit run src/app.py

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "flame_in_freefall.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Succesfully deleted compilation/temporal files"

.PHONY: install run clean
