"""persist planner input facts

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Asia/Seoul",
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_tasks_id_workspace_id", "tasks", ["id", "workspace_id"])
    op.create_check_constraint(
        op.f("ck_tasks_unknown_time_forbids_instant"),
        "tasks",
        "(deadline_time_known = true) OR (deadline_at IS NULL)",
    )

    op.add_column("task_dependencies", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE task_dependencies AS dependency "
        "SET workspace_id = task.workspace_id "
        "FROM tasks AS task "
        "WHERE task.id = dependency.predecessor_id"
    )
    op.alter_column("task_dependencies", "workspace_id", nullable=False)
    op.create_index(
        op.f("ix_task_dependencies_workspace_id"),
        "task_dependencies",
        ["workspace_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_task_dependencies_workspace_id_workspaces"),
        "task_dependencies",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        op.f("fk_task_dependencies_predecessor_id_tasks"),
        "task_dependencies",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_task_dependencies_successor_id_tasks"),
        "task_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_task_dependencies_predecessor_workspace",
        "task_dependencies",
        "tasks",
        ["predecessor_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_task_dependencies_successor_workspace",
        "task_dependencies",
        "tasks",
        ["successor_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "external_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("deliverable", sa.String(length=200), nullable=False),
        sa.Column("owner_label", sa.String(length=120), nullable=True),
        sa.Column("expected_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uncertainty_buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("fallback_available", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
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
            "uncertainty_buffer_minutes >= 0",
            name=op.f("ck_external_dependencies_buffer_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_external_dependencies_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_dependencies")),
        sa.UniqueConstraint("id", "workspace_id", name="uq_external_dependencies_id_workspace_id"),
    )
    op.create_index(
        op.f("ix_external_dependencies_workspace_id"),
        "external_dependencies",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "external_dependency_tasks",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("external_dependency_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.CheckConstraint(
            "role IN ('affected', 'fallback')",
            name=op.f("ck_external_dependency_tasks_valid_role"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_external_dependency_tasks_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["external_dependency_id", "workspace_id"],
            ["external_dependencies.id", "external_dependencies.workspace_id"],
            name="fk_external_dependency_tasks_dependency_workspace",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "workspace_id"],
            ["tasks.id", "tasks.workspace_id"],
            name="fk_external_dependency_tasks_task_workspace",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "external_dependency_id",
            "task_id",
            "role",
            name=op.f("pk_external_dependency_tasks"),
        ),
    )
    op.create_index(
        op.f("ix_external_dependency_tasks_workspace_id"),
        "external_dependency_tasks",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "workspace_excluded_dates",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("excluded_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_workspace_excluded_dates_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "workspace_id", "excluded_date", name=op.f("pk_workspace_excluded_dates")
        ),
    )


def downgrade() -> None:
    op.drop_table("workspace_excluded_dates")
    op.drop_index(
        op.f("ix_external_dependency_tasks_workspace_id"),
        table_name="external_dependency_tasks",
    )
    op.drop_table("external_dependency_tasks")
    op.drop_index(op.f("ix_external_dependencies_workspace_id"), table_name="external_dependencies")
    op.drop_table("external_dependencies")

    op.drop_constraint(
        "fk_task_dependencies_successor_workspace", "task_dependencies", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_task_dependencies_predecessor_workspace", "task_dependencies", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_task_dependencies_workspace_id_workspaces"),
        "task_dependencies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_task_dependencies_predecessor_id_tasks"),
        "task_dependencies",
        "tasks",
        ["predecessor_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_task_dependencies_successor_id_tasks"),
        "task_dependencies",
        "tasks",
        ["successor_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(op.f("ix_task_dependencies_workspace_id"), table_name="task_dependencies")
    op.drop_column("task_dependencies", "workspace_id")
    op.drop_constraint(op.f("ck_tasks_unknown_time_forbids_instant"), "tasks", type_="check")
    op.drop_constraint("uq_tasks_id_workspace_id", "tasks", type_="unique")
    op.drop_column("workspaces", "timezone")
