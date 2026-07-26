# Todos os comandos rodam em container: não há Python nem uv instalados no host,
# e é isso que faz o ambiente ser o mesmo para qualquer pessoa (e no CI).

COMPOSE   := docker compose
# Lida do Dockerfile para não haver dois digests a manter em sincronia: o lock e
# a imagem têm de ser resolvidos pelo mesmo uv e pelo mesmo Python.
UV_IMAGE  := $(shell sed -n 's/^ARG UV_IMAGE=//p' Dockerfile)
IN_APP    := $(COMPOSE) run --rm --no-deps app
WITH_DB   := $(COMPOSE) run --rm app

.DEFAULT_GOAL := help

.PHONY: help
help: ## Lista os alvos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- ambiente ---------------------------------------------------------------

.PHONY: env
env: ## Cria o .env a partir do exemplo, se ainda não existir
	@test -f .env || (cp .env.example .env && echo ".env criado a partir de .env.example")

.PHONY: up
up: env ## Sobe app e banco (http://localhost:8000)
	$(COMPOSE) up --build

.PHONY: down
down: ## Derruba os containers (mantém o volume do banco)
	$(COMPOSE) down

.PHONY: clean
clean: ## Derruba os containers e apaga o volume do banco
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Acompanha o log da aplicação
	$(COMPOSE) logs -f app

.PHONY: sh
sh: env ## Abre um shell no container da aplicação
	$(IN_APP) bash

# --- verificação ------------------------------------------------------------

.PHONY: fmt
fmt: env ## Formata o código
	$(IN_APP) ruff format app tests
	$(IN_APP) ruff check --fix app tests

.PHONY: lint
lint: env ## Formatação e regras (Ruff)
	$(IN_APP) ruff format --check app tests
	$(IN_APP) ruff check app tests

.PHONY: typecheck
typecheck: env ## Tipos (mypy, modo estrito)
	$(IN_APP) mypy app tests

.PHONY: test
test: env ## Suíte de testes com cobertura (exige o banco)
	$(WITH_DB) pytest

.PHONY: check
check: lint typecheck test ## Tudo que o CI exige antes de integrar

# --- banco ------------------------------------------------------------------

.PHONY: migrate
migrate: env ## Aplica as migrações pendentes
	$(WITH_DB) alembic upgrade head

.PHONY: revision
revision: env ## Nova migração: make revision m="mensagem"
	$(WITH_DB) alembic revision --autogenerate -m "$(m)"

# --- artefato ---------------------------------------------------------------

.PHONY: build
build: ## Constrói a imagem de execução com o identificador de build injetado
	docker build --target runtime \
		--build-arg APP_VERSION=$$(git describe --tags --always --dirty) \
		--build-arg APP_COMMIT=$$(git rev-parse HEAD) \
		-t nudge:local .

.PHONY: lock
lock: ## Regera o uv.lock (a única coisa que precisa da imagem do uv)
	@# --user e UV_CACHE_DIR: sem eles o uv escreve o lock como root no seu
	@# repositório. O container de dev não serve aqui — o uv.lock que existe
	@# dentro dele é a cópia assada no build, não o arquivo versionado.
	docker run --rm \
		--user "$(shell id -u):$(shell id -g)" \
		-e UV_CACHE_DIR=/tmp/uv-cache -e HOME=/tmp \
		-v "$(CURDIR)":/w -w /w $(UV_IMAGE) uv lock

.PHONY: files
files: ## Conta os arquivos de código do aplicativo (teto de 20, ADR-0010)
	@find app -type f \
		\( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.mako' \) \
		-not -path '*/__pycache__/*' | sort | sed 's/^/  /'
	@printf 'total: %s (teto: 20)\n' "$$(find app -type f \
		\( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.mako' \) \
		-not -path '*/__pycache__/*' | wc -l)"
