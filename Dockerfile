# Construção em múltiplos estágios: a imagem final não tem ferramenta de build.
# Bases fixadas por digest — nunca tag móvel (TRD plataforma).
# O ambiente virtual vive fora de /app para que o bind mount de desenvolvimento
# possa cobrir /app sem esconder as dependências.

ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca
ARG RUNTIME_IMAGE=python:3.13-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

# --- dependências -----------------------------------------------------------
FROM ${UV_IMAGE} AS deps
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock ./

FROM deps AS builder
# `--locked`, não `--frozen`: exige que o uv.lock esteja em dia com o
# pyproject.toml. `--frozen` só usaria o lock como está, e uma dependência
# adicionada sem `make lock` produziria imagem que constrói limpa e quebra em
# tempo de import.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- desenvolvimento e verificação (lint, tipos, testes) --------------------
# O código é montado em /app pelo compose; nada é copiado para dentro.
FROM deps AS dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
# UID 1000 para que os artefatos escritos no bind mount pertençam ao operador.
# /app precisa ser escrevível: é ali que ruff, mypy e pytest guardam cache — em
# camada efêmera, não no repositório montado.
RUN useradd --create-home --uid 1000 nudge \
    && chown -R nudge:nudge /opt/venv /app
USER 1000:1000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- execução ---------------------------------------------------------------
FROM ${RUNTIME_IMAGE} AS runtime

ARG APP_VERSION=0.0.0-dev
ARG APP_COMMIT=unknown
ENV APP_VERSION=${APP_VERSION} \
    APP_COMMIT=${APP_COMMIT} \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

LABEL org.opencontainers.image.title="nudge" \
      org.opencontainers.image.source="https://github.com/GabrielWillers/nudge" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_COMMIT}"

RUN groupadd --system --gid 10001 nudge \
    && useradd --system --uid 10001 --gid nudge --no-create-home nudge

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY app ./app

# Sem privilégio, e nada dentro de /app precisa de escrita: o sistema de
# arquivos raiz pode ser montado somente para leitura.
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
