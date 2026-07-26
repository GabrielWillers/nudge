"""Testes dos predicados de operabilidade do PRD.

São os quatro pontos de contato com a plataforma (ADR-0010): sonda de
vivacidade, sonda de prontidão, métricas e identificador de build.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import db
from app.config import get_settings


def unreachable_engine() -> object:
    """Banco inalcançável: porta 1 em loopback, sem espera."""
    return create_engine(
        "postgresql+psycopg://ninguem:nada@127.0.0.1:1/vazio",
        connect_args={"connect_timeout": 1},
    )


def test_healthz_responde_sucesso_com_identificador_de_build(
    client: TestClient,
) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == get_settings().app_version
    assert body["commit"] == get_settings().app_commit


def test_healthz_nao_toca_o_banco(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invariante do PRD: se `/healthz` dependesse do banco, uma
    indisponibilidade dele causaria reinício em laço."""

    def explode() -> object:
        raise AssertionError("/healthz não pode tocar o banco")

    monkeypatch.setattr(db, "get_engine", explode)

    assert client.get("/healthz").status_code == 200


def test_readyz_responde_sucesso_com_banco_alcancavel(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_readyz_falha_com_banco_inalcancavel(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(db, "get_engine", unreachable_engine)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["database"] == "down"


def test_metricas_expoem_contagem_latencia_e_erro_por_rota(
    client: TestClient,
) -> None:
    client.get("/")
    client.post("/reminders/nao-e-uuid/delete")  # produz um 404

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    corpo = metrics.text
    assert "http_requests_total" in corpo
    assert "http_request_duration_seconds" in corpo
    assert 'handler="/"' in corpo
    assert 'status="4xx"' in corpo or 'status="404"' in corpo


def test_identificador_de_build_visivel_na_pagina_e_igual_ao_healthz(
    client: TestClient,
) -> None:
    page = client.get("/").text
    health = client.get("/healthz").json()
    version_endpoint = client.get("/version").json()

    assert health["version"] in page
    assert health["commit"] in page
    assert version_endpoint == {
        "version": health["version"],
        "commit": health["commit"],
    }


def test_partida_sem_database_url_falha_com_mensagem_explicita(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            get_settings()
    finally:
        # Devolve o cache ao estado que o resto da suíte espera.
        get_settings.cache_clear()


def test_estilo_e_servido_pelo_proprio_aplicativo(client: TestClient) -> None:
    """Um arquivo de estilo, servido pelo próprio serviço. A asserção é sobre o
    contrato (existe e é CSS), não sobre o conteúdo — trocar a paleta não pode
    quebrar teste."""
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_favicon_e_servido_pelo_proprio_aplicativo(client: TestClient) -> None:
    """Declarado no HTML e servido daqui: sem isso o navegador pede
    `/favicon.ico` na raiz e cada acesso vira um 404 no log e na métrica."""
    page = client.get("/").text
    assert "/static/favicon.svg" in page

    response = client.get("/static/favicon.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_endereco_do_estilo_carrega_o_identificador_de_build(
    client: TestClient,
) -> None:
    """Sem isso, um deploy que muda só o estilo pode ficar invisível: /static
    não manda Cache-Control e o navegador reaproveita o arquivo antigo."""
    page = client.get("/").text
    settings = get_settings()

    assert f"style.css?v={settings.app_version}-{settings.app_commit}" in page


def test_pagina_nao_busca_recurso_de_terceiro(client: TestClient) -> None:
    """Nada na página sai do serviço: sem CDN, sem fonte externa, sem
    empacotador (ADR-0010)."""
    page = client.get("/").text

    assert "fonts.googleapis.com" not in page
    assert "cdn." not in page
    assert "<script" not in page
