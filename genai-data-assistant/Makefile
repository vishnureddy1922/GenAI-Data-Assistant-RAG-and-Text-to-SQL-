.PHONY: help env setup up down logs ingest test cov lint eval eval-sql api ui

help:     ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-9s %s\n", $$1, $$2}'

env:      ## Create .env from the example (then add your API key)
	@test -f .env || cp .env.example .env

setup:    ## Install dev dependencies
	pip install -r requirements-dev.txt -r requirements-ui.txt

up: env   ## Start Postgres+pgvector, ingest docs, API and UI
	docker compose up -d --build

down:     ## Stop everything
	docker compose down

logs:     ## Tail API logs
	docker compose logs -f api

ingest:   ## Re-embed the knowledge base
	python -m app.ingest

api:      ## Run the API locally with reload
	uvicorn app.api:app --reload

ui:       ## Run the Streamlit UI locally
	streamlit run ui/streamlit_app.py

test:     ## Unit tests (no API key or database needed)
	pytest

cov:      ## Tests with coverage
	pytest --cov --cov-report=term-missing

lint:     ## Ruff
	ruff check . && ruff format --check .

eval:     ## Full evaluation: routing, SQL execution accuracy, RAGAS
	python -m eval.run_eval

eval-sql: ## Evaluation without RAGAS (cheaper)
	python -m eval.run_eval --skip-ragas
