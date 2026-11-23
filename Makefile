.PHONY: install install-dev lint format test seed run-api run-ui run-mcp docker-build docker-up docker-down clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-lock.txt

lint:
	flake8 --max-line-length=120 .

format:
	ruff format src tests main.py seed_db.py

test:
	python -m pytest -v

seed:
	python seed_db.py

run-api:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	streamlit run src/frontend/app.py

run-mcp:
	python -m src.mcp_server.server

docker-build:
	docker build -t cv-nexus:latest .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build
