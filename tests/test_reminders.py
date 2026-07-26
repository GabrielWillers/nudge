"""Testes dos predicados de produto do PRD `nudge-app-v1`.

Cada teste referencia o predicado que exercita — os testes são escritos contra
os predicados, não contra a implementação.
"""

import base64
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Reminder
from tests.conftest import AddReminder


def count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Reminder)) or 0


def reload(session: Session, reminder_id: uuid.UUID) -> Reminder:
    session.expire_all()
    found = session.get(Reminder, reminder_id, populate_existing=True)
    assert found is not None
    return found


def test_cria_lembrete_valido_e_aparece_na_lista(
    client: TestClient, session: Session
) -> None:
    """Título e vencimento válidos: o lembrete passa a existir e aparece."""
    created = client.post(
        "/reminders",
        data={"title": "Pagar a fatura", "due_at": "2026-08-01T09:30"},
        follow_redirects=False,
    )

    # post/redirect/get: nunca se renderiza resposta direto de um POST.
    assert created.status_code == 303
    assert created.headers["location"] == "/"

    listed = client.get("/")
    assert listed.status_code == 200
    assert "Pagar a fatura" in listed.text
    assert count(session) == 1


def test_lista_ordenada_por_vencimento_crescente(
    client: TestClient, add_reminder: AddReminder
) -> None:
    add_reminder(title="Terceiro", due_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC))
    add_reminder(title="Primeiro", due_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC))
    add_reminder(title="Segundo", due_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC))

    page = client.get("/").text

    assert page.index("Primeiro") < page.index("Segundo") < page.index("Terceiro")


def test_marcar_concluido_e_desmarcar(
    client: TestClient, session: Session, add_reminder: AddReminder
) -> None:
    reminder = add_reminder(title="Regar as plantas")

    marked = client.post(f"/reminders/{reminder.id}/toggle", follow_redirects=False)
    assert marked.status_code == 303
    assert reload(session, reminder.id).completed is True
    assert "concluido" in client.get("/").text

    client.post(f"/reminders/{reminder.id}/toggle", follow_redirects=False)
    assert reload(session, reminder.id).completed is False


def test_apagar_lembrete_nao_volta_ao_recarregar(
    client: TestClient, session: Session, add_reminder: AddReminder
) -> None:
    reminder = add_reminder(title="Trocar o filtro")

    deleted = client.post(f"/reminders/{reminder.id}/delete", follow_redirects=False)

    assert deleted.status_code == 303
    assert "Trocar o filtro" not in client.get("/").text
    assert "Trocar o filtro" not in client.get("/").text  # recarregar
    assert count(session) == 0


def test_titulo_vazio_e_recusado_com_mensagem_na_pagina(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/reminders", data={"title": "   ", "due_at": "2026-08-01T09:30"}
    )

    # O cliente segue o 303 e termina na lista, com a mensagem na página.
    assert response.status_code == 200
    assert str(response.url).endswith("/")
    assert "Informe um título" in response.text
    assert count(session) == 0


def test_erro_de_validacao_tambem_redireciona(
    client: TestClient, session: Session
) -> None:
    """Nada é renderizado direto de um POST, nem quando a validação falha —
    do contrário recarregar a página de erro reenviaria o formulário."""
    response = client.post(
        "/reminders",
        data={"title": "", "due_at": "2026-08-01T09:30"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert count(session) == 0


def test_mensagem_de_erro_aparece_uma_vez_e_some(
    client: TestClient, session: Session
) -> None:
    resposta = client.post(
        "/reminders", data={"title": "", "due_at": "2026-08-01T09:30"}
    )
    assert "Informe um título" in resposta.text

    # Recarregar não repete a mensagem: o cookie é consumido na exibição.
    assert "Informe um título" not in client.get("/").text


def test_cookie_de_mensagem_corrompido_e_ignorado(client: TestClient) -> None:
    """O cookie vem do navegador, então pode chegar de qualquer jeito: a
    página não pode quebrar por causa dele."""
    client.cookies.set("nudge_flash", "isto-nao-e-base64-valido!!")
    assert client.get("/").status_code == 200

    # Base64 válido, mas o conteúdo não é um objeto.
    client.cookies.set(
        "nudge_flash", base64.urlsafe_b64encode(b'["lista", "nao", "objeto"]').decode()
    )
    response = client.get("/")

    assert response.status_code == 200
    assert "Nenhum lembrete" in response.text


def test_titulo_acima_de_200_caracteres_e_recusado(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/reminders", data={"title": "a" * 201, "due_at": "2026-08-01T09:30"}
    )

    assert response.status_code == 200
    assert "no máximo 200 caracteres" in response.text
    assert count(session) == 0


def test_titulo_com_exatamente_200_caracteres_e_aceito(
    client: TestClient, session: Session
) -> None:
    response = client.post(
        "/reminders",
        data={"title": "a" * 200, "due_at": "2026-08-01T09:30"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert count(session) == 1


def test_vencimento_invalido_e_recusado(client: TestClient, session: Session) -> None:
    response = client.post(
        "/reminders", data={"title": "Comprar pão", "due_at": "ontem à tarde"}
    )

    assert response.status_code == 200
    assert "vencimento válido" in response.text
    assert count(session) == 0
    # A entrada volta preenchida no formulário, para não obrigar a redigitar.
    assert "Comprar pão" in response.text


def test_vencimento_vazio_e_recusado(client: TestClient, session: Session) -> None:
    response = client.post("/reminders", data={"title": "Comprar pão", "due_at": ""})

    assert response.status_code == 200
    assert "vencimento válido" in response.text
    assert count(session) == 0


def test_vencimento_com_fuso_representa_o_mesmo_instante_absoluto(
    client: TestClient, session: Session
) -> None:
    """Ida e volta de fuso: 09:30 em -03:00 é 12:30 UTC."""
    client.post(
        "/reminders",
        data={"title": "Reunião", "due_at": "2026-08-01T09:30:00-03:00"},
        follow_redirects=False,
    )

    stored = session.scalars(select(Reminder)).one()
    assert stored.due_at.astimezone(UTC) == datetime(2026, 8, 1, 12, 30, tzinfo=UTC)


def test_vencimento_sem_fuso_e_interpretado_no_fuso_da_aplicacao(
    client: TestClient, session: Session
) -> None:
    """O formulário não carrega fuso; a borda interpreta em APP_TIMEZONE
    (America/Sao_Paulo, -03:00) e grava em UTC."""
    client.post(
        "/reminders",
        data={"title": "Dentista", "due_at": "2026-08-01T09:30"},
        follow_redirects=False,
    )

    stored = session.scalars(select(Reminder)).one()
    assert stored.due_at.astimezone(UTC) == datetime(2026, 8, 1, 12, 30, tzinfo=UTC)
    # E a página reconverte para exibição, em português.
    page = client.get("/").text
    assert "sáb, 01 ago 2026 · 09:30" in page
    # O valor de máquina continua em UTC, no atributo `datetime`.
    assert 'datetime="2026-08-01T12:30:00+00:00"' in page


def test_lista_vazia_tem_estado_vazio_explicito(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Nenhum lembrete" in response.text


def test_identificador_inexistente_responde_nao_encontrado(
    client: TestClient, session: Session, add_reminder: AddReminder
) -> None:
    add_reminder(title="Intacto")
    ausente = uuid.uuid4()

    assert client.post(f"/reminders/{ausente}/toggle").status_code == 404
    assert client.post(f"/reminders/{ausente}/delete").status_code == 404
    # Identificador que não é nem UUID também é "não encontrado", não erro de
    # validação.
    assert client.post("/reminders/nao-e-uuid/toggle").status_code == 404
    assert count(session) == 1


def test_titulo_com_marcacao_html_e_exibido_escapado(client: TestClient) -> None:
    """Injeção de HTML é a superfície de ataque real deste aplicativo: a
    entrada do visitante é reexibida na página."""
    client.post(
        "/reminders",
        data={"title": "<script>alert('x')</script>", "due_at": "2026-08-01T09:30"},
        follow_redirects=False,
    )

    page = client.get("/").text

    assert "<script>alert" not in page
    assert "&lt;script&gt;alert" in page


def test_corpo_acima_do_limite_e_recusado(client: TestClient, session: Session) -> None:
    response = client.post(
        "/reminders",
        data={"title": "a" * 20_000, "due_at": "2026-08-01T09:30"},
    )

    assert response.status_code == 413
    assert count(session) == 0
