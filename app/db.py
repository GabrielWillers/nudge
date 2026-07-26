"""Acesso a dados: SQLAlchemy 2 síncrono + psycopg (ADR-0010).

Síncrono é deliberado — um aplicativo que renderiza página não ganha nada com
assincronia.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependência de requisição: uma sessão por requisição, sempre fechada."""
    with _session_factory()() as session:
        yield session


def database_ready() -> bool:
    """Usada só pela sonda de prontidão. `/healthz` nunca chama isto."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
