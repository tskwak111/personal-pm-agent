"""persist encrypted calendar connections

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("scopes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("access_token_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("access_token_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("token_key_version", sa.Integer(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mode IN ('READ_ONLY','READ_WRITE')",
            name=op.f("ck_calendar_connections_valid_mode"),
        ),
        sa.CheckConstraint(
            "status IN ('CONNECTED','NEEDS_REAUTHORIZATION','REVOKED')",
            name=op.f("ck_calendar_connections_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_calendar_connections_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_connections")),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            name="uq_calendar_connections_workspace_provider",
        ),
    )
    op.create_index(
        op.f("ix_calendar_connections_workspace_id"),
        "calendar_connections",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_calendar_connections_workspace_id"),
        table_name="calendar_connections",
    )
    op.drop_table("calendar_connections")
