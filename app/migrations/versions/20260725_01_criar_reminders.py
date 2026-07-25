"""criar tabela reminders

Revision ID: 20260725_01
Revises:
Create Date: 2026-07-25

Única tabela do sistema (ADR-0010): sem tabela de usuários e sem coluna de dono.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "completed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reminders"),
    )
    # Atende diretamente a consulta da lista, ordenada por vencimento.
    op.create_index("ix_reminders_due_at", "reminders", ["due_at"])


def downgrade() -> None:
    op.drop_index("ix_reminders_due_at", table_name="reminders")
    op.drop_table("reminders")
