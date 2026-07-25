"""Rotas de página.

Escrita é sempre POST seguido de redirecionamento 303 para a lista
(*post/redirect/get*): nunca se renderiza resposta direto de um POST, para que
recarregar não reenvie o formulário.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import Reminder
from app.timeutil import format_display, parse_due_at

MAX_TITLE_LENGTH = 200

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2Templates já vem com escape automático ligado, e ele nunca é desligado:
# o título do visitante é reexibido na página, então injeção de HTML é a
# superfície de ataque real deste aplicativo (TRD).
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["display"] = format_display

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def _render_list(
    request: Request,
    session: Session,
    *,
    status_code: int = 200,
    error: str | None = None,
    title: str = "",
    due_at: str = "",
) -> HTMLResponse:
    reminders = session.scalars(select(Reminder).order_by(Reminder.due_at.asc())).all()
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "reminders": reminders,
            "error": error,
            "form": {"title": title, "due_at": due_at},
            "version": settings.app_version,
            "commit": settings.app_commit,
            "timezone": settings.app_timezone,
        },
        status_code=status_code,
    )


def _get_or_404(session: Session, reminder_id: str) -> Reminder:
    try:
        parsed_id = uuid.UUID(reminder_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="lembrete não encontrado") from None
    reminder = session.get(Reminder, parsed_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="lembrete não encontrado")
    return reminder


@router.get("/", response_class=HTMLResponse)
def list_reminders(request: Request, session: SessionDep) -> HTMLResponse:
    return _render_list(request, session)


# `response_model=None`: a rota devolve página (erro) ou redirecionamento
# (sucesso), e nenhum dos dois é um modelo a ser serializado.
@router.post("/reminders", response_model=None)
def create_reminder(
    request: Request,
    session: SessionDep,
    title: Annotated[str, Form()] = "",
    due_at: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    # Validação no servidor, sempre — nunca só no formulário.
    clean_title = title.strip()
    if not clean_title:
        return _render_list(
            request,
            session,
            status_code=422,
            error="Informe um título para o lembrete.",
            title=title,
            due_at=due_at,
        )
    if len(clean_title) > MAX_TITLE_LENGTH:
        return _render_list(
            request,
            session,
            status_code=422,
            error=f"O título deve ter no máximo {MAX_TITLE_LENGTH} caracteres.",
            title=title,
            due_at=due_at,
        )
    try:
        due_at_utc = parse_due_at(due_at)
    except ValueError:
        return _render_list(
            request,
            session,
            status_code=422,
            error="Informe um vencimento válido (data e hora).",
            title=title,
            due_at=due_at,
        )

    session.add(Reminder(title=clean_title, due_at=due_at_utc))
    session.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/reminders/{reminder_id}/toggle")
def toggle_reminder(reminder_id: str, session: SessionDep) -> RedirectResponse:
    reminder = _get_or_404(session, reminder_id)
    reminder.completed = not reminder.completed
    session.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/reminders/{reminder_id}/delete")
def delete_reminder(reminder_id: str, session: SessionDep) -> RedirectResponse:
    reminder = _get_or_404(session, reminder_id)
    session.delete(reminder)
    session.commit()
    return RedirectResponse(url="/", status_code=303)
