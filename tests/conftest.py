"""Infraestrutura da suíte.

Os testes rodam contra um PostgreSQL de verdade — o mesmo major da produção.
SQLite não serviria: `timestamptz` e `uuid` são exatamente o que precisa ser
exercitado.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://nudge:nudge-local-dev-only@db:5432/nudge_test"
)

# O ambiente precisa estar montado ANTES de importar qualquer módulo do
# aplicativo: a configuração é lida uma única vez, na primeira chamada.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_TIMEZONE", "America/Sao_Paulo")
os.environ.setdefault("APP_VERSION", "9.9.9-test")
os.environ.setdefault("APP_COMMIT", "1234567890abcdef")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, run_migrations  # noqa: E402
from app.models import Reminder  # noqa: E402

AddReminder = Callable[..., Reminder]


def with_database(url: str, name: str) -> str:
    """A mesma URL apontando para outro banco do mesmo servidor."""
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


def maintenance_url(url: str) -> str:
    """A URL do banco `postgres`, o único que existe antes de criarmos os
    nossos."""
    return with_database(url, "postgres")


def database_name(url: str) -> str:
    return urlsplit(url).path.lstrip("/")


def ensure_database(url: str) -> None:
    """Cria o banco se ele ainda não existir — mantém `docker compose` sem
    passo manual."""
    name = database_name(url)
    admin = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    ensure_database(TEST_DATABASE_URL)
    run_migrations()
    created = create_engine(TEST_DATABASE_URL)
    yield created
    created.dispose()


@pytest.fixture(autouse=True)
def clean_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE reminders"))


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as opened:
        yield opened


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    # O `with` dispara o ciclo de vida: é ele que aplica as migrações antes de
    # o serviço atender.
    with TestClient(app) as opened:
        yield opened


@pytest.fixture
def add_reminder(session: Session) -> AddReminder:
    """Insere um lembrete direto no banco, sem passar pelas rotas."""

    def _add(
        title: str = "Lembrete",
        due_at: datetime | None = None,
        completed: bool = False,
    ) -> Reminder:
        reminder = Reminder(
            title=title,
            due_at=due_at or datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            completed=completed,
        )
        session.add(reminder)
        session.commit()
        return reminder

    return _add
