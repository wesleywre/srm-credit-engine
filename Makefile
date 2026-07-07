.DEFAULT_GOAL := help

.PHONY: help install hooks up down dev-api dev-web test test-api test-web lint format

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Instala as dependências (backend e frontend)
	cd backend && uv sync
	cd frontend && npm install

hooks: ## Instala os git hooks (pre-commit, commit-msg, pre-push)
	cd backend && uv run pre-commit install --install-hooks

up: ## Sobe a stack completa (docker compose)
	docker compose up --build -d

down: ## Derruba a stack
	docker compose down

dev-api: ## Roda o backend em modo dev (hot reload)
	cd backend && uv run uvicorn app.main:app --reload

dev-web: ## Roda o frontend em modo dev
	cd frontend && npm run dev

test: test-api test-web ## Roda todos os testes

test-api: ## Testes do backend
	cd backend && uv run pytest

test-web: ## Testes do frontend
	cd frontend && npm run test

lint: ## Linters e type checkers (backend e frontend)
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd frontend && npm run lint && npm run format:check && npm run typecheck

format: ## Formata o código
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && npm run format
