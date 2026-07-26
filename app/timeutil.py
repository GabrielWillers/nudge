"""Fronteira de fuso horário.

Invariante do PRD: todo instante é gravado e devolvido em UTC. A conversão
acontece só aqui — na borda de entrada e na formatação da página.

O formulário HTML usa `datetime-local`, que não carrega fuso, e o ADR-0010
proíbe JavaScript de aplicação: não há como o fuso do navegador chegar ao
servidor. Entrada sem fuso é portanto interpretada em `APP_TIMEZONE`. Entrada
com fuso explícito (ISO 8601 com offset) é respeitada como está.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings

# Interface em português, língua única (PRD): as abreviações ficam aqui em vez
# de depender do locale do sistema operacional, que no container é `C`.
DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
MESES = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


def app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def parse_due_at(raw: str) -> datetime:
    """Converte a entrada do formulário em um instante absoluto em UTC.

    Levanta `ValueError` para formato inválido — o chamador transforma isso em
    mensagem na própria página.
    """
    candidate = raw.strip()
    if not candidate:
        raise ValueError("vencimento vazio")
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=app_timezone())
    return parsed.astimezone(UTC)


def to_local(instant: datetime) -> datetime:
    """UTC (ou naive, tratado como UTC) para o fuso de exibição."""
    aware = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant
    return aware.astimezone(app_timezone())


def format_display(instant: datetime) -> str:
    """Formato de leitura: `sáb, 01 ago 2026 · 09:30`.

    Absoluto de propósito — nada de "hoje" ou "em 2 dias": data relativa
    depende do instante da renderização, o que muda a página sem mudar o dado.
    """
    local = to_local(instant)
    dia = DIAS[local.weekday()]
    mes = MESES[local.month - 1]
    return f"{dia}, {local.day:02d} {mes} {local.year} · {local:%H:%M}"
