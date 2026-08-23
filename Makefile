.PHONY: bootstrap format-check lint typecheck test-unit test-integration test-e2e \
        build verify-planner verify-api verify-web verify-docs verify-repo verify

bootstrap:
	uv sync
	pnpm install

format-check:
	uv run ruff format --check tests packages/planner/src apps/api/src apps/worker/src scripts
	pnpm -r format:check

lint:
	uv run ruff check .
	pnpm -r lint

typecheck:
	uv run mypy packages/planner/src apps/api/src apps/worker/src
	pnpm -r typecheck

test-unit:
	uv run pytest -m "not integration and not e2e"
	pnpm -r test --run

test-integration:
	APP_ENVIRONMENT=test PM_DATABASE_URL="postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm" uv run pytest apps/api/tests/integration packages/planner/tests -q -m "integration or not integration"

test-e2e:
	pnpm -r e2e

build:
	pnpm -r build

verify-planner:
	uv run --package personal-pm-planner pytest packages/planner/tests -q

verify-api:
	uv run --package personal-pm-api pytest apps/api/tests -q

verify-web:
	pnpm --filter @personal-pm/web test --run
	pnpm --filter @personal-pm/web typecheck
	pnpm --filter @personal-pm/web build

verify-docs:
	python3 scripts/verify_package.py

verify-repo:
	python3 scripts/verify_repo.py

verify: format-check lint typecheck test-unit build verify-docs verify-repo
