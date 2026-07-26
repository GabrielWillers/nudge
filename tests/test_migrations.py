"""Migração de schema e o índice que atende a consulta da lista."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect, text

from app.main import APP_DIR
from app.models import Reminder
from tests.conftest import (
    TEST_DATABASE_URL,
    database_name,
    ensure_database,
    maintenance_url,
    with_database,
)

SCRATCH_URL = with_database(
    TEST_DATABASE_URL, f"{database_name(TEST_DATABASE_URL)}_migracao"
)


def alembic_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(APP_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture
def scratch_engine() -> Iterator[Engine]:
    """Banco descartável: a migração é exercitada do zero, não sobre o banco
    que os outros testes usam."""
    ensure_database(SCRATCH_URL)
    engine = create_engine(SCRATCH_URL)
    yield engine
    engine.dispose()
    admin = create_engine(maintenance_url(SCRATCH_URL), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{database_name(SCRATCH_URL)}"'))
    admin.dispose()


def test_migracao_sobe_de_banco_vazio_e_desce_um_passo(
    scratch_engine: Engine,
) -> None:
    config = alembic_config(SCRATCH_URL)

    command.upgrade(config, "head")

    inspector = inspect(scratch_engine)
    assert "reminders" in inspector.get_table_names()
    indexes = {index["name"] for index in inspector.get_indexes("reminders")}
    assert "ix_reminders_due_at" in indexes
    columns = {column["name"] for column in inspector.get_columns("reminders")}
    assert columns == {"id", "title", "due_at", "completed", "created_at"}
    # Nenhuma tabela de usuários existe (ADR-0010).
    assert "users" not in inspector.get_table_names()

    command.downgrade(config, "-1")

    assert "reminders" not in inspect(scratch_engine).get_table_names()


def test_consulta_da_lista_usa_o_indice_de_due_at(engine: Engine) -> None:
    base = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    with engine.begin() as conn:
        for offset in range(500):
            conn.execute(
                text(
                    "INSERT INTO reminders (id, title, due_at, completed, created_at)"
                    " VALUES (gen_random_uuid(), :title, :due_at, false, now())"
                ),
                {
                    "title": f"Lembrete {offset}",
                    "due_at": base + timedelta(minutes=offset),
                },
            )
        conn.execute(text("ANALYZE reminders"))

    query = str(
        Reminder.__table__.select().order_by(Reminder.due_at.asc()).compile(engine)
    )
    with engine.connect() as conn:
        # Com poucas linhas o planejador prefere varredura sequencial; o que
        # está sob teste é a existência de um caminho por índice para esta
        # ordenação.
        conn.execute(text("SET enable_seqscan = off"))
        plan = "\n".join(
            row[0] for row in conn.execute(text(f"EXPLAIN {query}")).fetchall()
        )

    assert "ix_reminders_due_at" in plan
