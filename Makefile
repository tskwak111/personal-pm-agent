.PHONY: bootstrap format-check lint typecheck test-unit test-integration test-e2e \
        build verify-planner verify-api verify-web verify-docs verify-repo \
        verify-stage-a verify-stage-b verify-stage-c verify-release \
        verify-release-readiness verify

STAGE_A_REPORT ?= /tmp/pma-stage-a.json
STAGE_B_REPORT ?= /tmp/pma-stage-b.json
STAGE_C_REPORT ?= /tmp/pma-stage-c.json
RELEASE_REPORT ?= /tmp/pma-release.json
STAGE_A_SCENARIOS ?= 20000
OUTCOMES_REPORT ?= evals/reports/pilot/outcomes.json
INCIDENTS_REPORT ?= evals/reports/pilot/incidents.json
THRESHOLD_CHANGES_REPORT ?= evals/reports/pilot/threshold-changes.json

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
	APP_ENVIRONMENT=test PM_DATABASE_URL="postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm" uv run pytest apps/api/tests/integration packages/planner/tests -q

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

verify-stage-a:
	uv run python scripts/run_stage_a.py --scenarios $(STAGE_A_SCENARIOS) --output $(STAGE_A_REPORT)

verify-stage-b:
	uv run python scripts/run_stage_b.py --output $(STAGE_B_REPORT)

verify-stage-c:
	uv run python scripts/run_stage_c.py --output $(STAGE_C_REPORT)

verify-release:
	uv run python scripts/verify_release.py \
		--stage-a $(STAGE_A_REPORT) \
		--stage-b $(STAGE_B_REPORT) \
		--stage-c $(STAGE_C_REPORT) \
		--outcomes $(OUTCOMES_REPORT) \
		--incidents $(INCIDENTS_REPORT) \
		--threshold-changes $(THRESHOLD_CHANGES_REPORT) \
		--output $(RELEASE_REPORT)

verify-release-readiness:
	$(MAKE) verify-stage-a
	-$(MAKE) verify-stage-b
	$(MAKE) verify-stage-c
	$(MAKE) verify-release

verify: format-check lint typecheck test-unit build verify-docs verify-repo verify-stage-a verify-stage-c
