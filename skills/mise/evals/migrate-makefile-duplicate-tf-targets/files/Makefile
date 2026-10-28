include .env
export

ENV ?= dev
TF_DIR := infra/$(ENV)

.PHONY: help install deps test test-unit lint fmt ci run docker-build tf-init tf-plan tf-apply terraform-plan terraform-apply terraform-apply-development tf-plan-prod deploy-staging deploy-prod migrate

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | cut -d: -f1

install:
	uv sync

deps: install

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

ci: lint test

run:
	uv run uvicorn acme_api.main:app --reload

docker-build:
	docker build -t acme-api:latest .

tf-init:
	terraform -chdir=$(TF_DIR) init

tf-plan: tf-init
	terraform -chdir=$(TF_DIR) plan

tf-apply: tf-init
	terraform -chdir=$(TF_DIR) apply

terraform-plan:
	cd infra/$(ENV) && terraform init && terraform plan -out=tfplan

terraform-apply:
	cd infra/$(ENV) && terraform apply -auto-approve tfplan

terraform-apply-development:
	cd infra/dev && terraform init && terraform apply -auto-approve

tf-plan-prod:
	terraform -chdir=infra/prod init
	terraform -chdir=infra/prod plan

deploy-staging:
	./scripts/deploy.sh staging

deploy-prod:
	./scripts/deploy.sh production

migrate:
	uv run alembic upgrade head
