"""Rotas de página.

Escrita é **sempre** POST seguido de redirecionamento 303 para a lista
(*post/redirect/get*), inclusive quando a validação falha: nada é renderizado
direto de um POST, para que recarregar não reenvie o formulário.

Como o erro não pode mais viajar no corpo da resposta, ele vai num cookie de
vida curta — lido e apagado na renderização seguinte.
"""

import base64
import binascii
import json
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import Reminder
from app.timeutil import format_display, parse_due_at

MAX_TITLE_LENGTH = 200

# Cookie de mensagem: sobrevive a um redirecionamento e morre em seguida.
FLASH_COOKIE = "nudge_flash"
FLASH_MAX_AGE = 60
FLASH_FIELDS = ("error", "title", "due_at")

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2Templates já vem com escape automático ligado, e ele nunca é desligado:
# o título do visitante é reexibido na página, então injeção de HTML é a
# superfície de ataque real deste aplicativo (TRD).
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["display"] = format_display

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def _write_flash(response: Response, error: str, title: str, due_at: str) -> None:
    """Guarda a mensagem e o que o visitante digitou até a próxima página.

    Base64 porque o valor é JSON com acento: cookie aceita um alfabeto
    estreito. Não é cifra e não precisa ser — o conteúdo não é segredo, é a
    mensagem que a própria pessoa acabou de provocar, e o template escapa
    tudo que vem daqui.
    """
    payload = json.dumps({"error": error, "title": title, "due_at": due_at})
    response.set_cookie(
        FLASH_COOKIE,
        base64.urlsafe_b64encode(payload.encode()).decode(),
        max_age=FLASH_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _read_flash(request: Request) -> dict[str, str]:
    """Devolve a mensagem pendente, ou vazio. Cookie corrompido é ignorado."""
    raw = request.cookies.get(FLASH_COOKIE)
    if not raw:
        return {}
    try:
        data = json.loads(base64.urlsafe_b64decode(raw.encode()))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {campo: str(data[campo]) for campo in FLASH_FIELDS if campo in data}


def _render_list(
    request: Request,
    session: Session,
    *,
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
    )


def _redirect_with_error(error: str, title: str, due_at: str) -> RedirectResponse:
    response = RedirectResponse(url="/", status_code=303)
    _write_flash(response, error, title, due_at)
    return response


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
    flash = _read_flash(request)
    response = _render_list(
        request,
        session,
        error=flash.get("error"),
        title=flash.get("title", ""),
        due_at=flash.get("due_at", ""),
    )
    if flash:
        # Exibida uma vez, some: recarregar não repete a mensagem.
        response.delete_cookie(FLASH_COOKIE, path="/")
    return response


@router.post("/reminders")
def create_reminder(
    session: SessionDep,
    title: Annotated[str, Form()] = "",
    due_at: Annotated[str, Form()] = "",
) -> RedirectResponse:
    # Validação no servidor, sempre — nunca só no formulário.
    clean_title = title.strip()
    if not clean_title:
        return _redirect_with_error("Informe um título para o lembrete.", title, due_at)
    if len(clean_title) > MAX_TITLE_LENGTH:
        return _redirect_with_error(
            f"O título deve ter no máximo {MAX_TITLE_LENGTH} caracteres.",
            title,
            due_at,
        )
    try:
        due_at_utc = parse_due_at(due_at)
    except ValueError:
        return _redirect_with_error(
            "Informe um vencimento válido (data e hora).", title, due_at
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
