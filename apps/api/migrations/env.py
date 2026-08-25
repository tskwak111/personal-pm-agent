"""Alembic environment for the Planning Core schema."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from personal_pm_api.approvals import models as approvals_models  # noqa: F401
from personal_pm_api.audit import models as audit_models  # noqa: F401
from personal_pm_api.calendar import models as calendar_models  # noqa: F401
from personal_pm_api.execution import models as execution_models  # noqa: F401
from personal_pm_api.identity import models as identity_models  # noqa: F401
from personal_pm_api.inbox import models as inbox_models  # noqa: F401
from personal_pm_api.planning import models as planning_models  # noqa: F401
from personal_pm_api.shared.idempotency import IdempotencyRecordModel  # noqa: F401
from personal_pm_api.shared.orm import Base
from personal_pm_api.workspaces import models as workspace_models  # noqa: F401
from sqlalchemy import engine_from_config, pool

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sync_url = os.environ.get(
    "PM_DATABASE_URL_SYNC",
    "postgresql+psycopg://personal_pm:local_only_password@localhost:15432/personal_pm",
)
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    context.configure(url=sync_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
