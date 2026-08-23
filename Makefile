.PHONY: help setup demo test clean sync

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Initial setup (install deps, init db)
	uv sync
	uv run dealflow db init
	@echo ""
	@echo "✅ Setup complete. Next: cp .env.example .env and add your OpenRouter key."

demo:  ## Run the full demo pipeline
	./examples/demo.sh

test:  ## Run tests
	uv run pytest -q

sync:  ## Sync to Airtable
	uv run dealflow sync-airtable

clean:  ## Remove generated files (db, cache, etc.)
	rm -rf data/*.sqlite
	rm -rf .pytest_cache
	rm -rf src/dealflow/__pycache__
	rm -rf src/dealflow/*/__pycache__
	@echo "✅ Cleaned. Run 'make setup' to reinitialize."
