# Phase 0 — Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a reproducible monorepo, local infrastructure, API/worker/web bootstraps, unified verification commands and CI without implementing product behavior.

**Architecture:** pnpm manages TypeScript workspaces and uv manages Python workspaces. The pure Planner package, FastAPI API, worker and Next.js web app start independently but share root quality commands and Docker Compose services.

**Tech Stack:** Python 3.13, uv, FastAPI 0.141.x, Node 24 LTS, pnpm 10.x, Next.js 16, React 19.2, PostgreSQL 18, Redis 8, MinIO-compatible local object storage, GitHub Actions.

**Spec:** `docs/specs/2026-08-23-personal-pm-agent-design.md` sections 18, 21 and 26; `docs/architecture/repository-and-module-contract.md`.

## Global Constraints

- Follow `AGENTS.md` and `docs/architecture/decision-precedence.md`.
- Never weaken Planner or Evaluation gates.
- Use TDD: failing test, confirmed failure, minimum implementation, focused pass, adjacent regression, commit.
- Keep files focused and interfaces explicit.
- Update `docs/status/IMPLEMENTATION_STATUS.md` after every completed Task.
- Do not claim completion without fresh command output.

---

## Locked File Map

```text
package.json                     root JS scripts and package manager pin
pnpm-workspace.yaml              TypeScript workspace members
pyproject.toml                   uv workspace and shared Python tooling
Makefile                         stable developer command contract
.env.example                     non-secret configuration names
compose.yaml                     PostgreSQL, Redis and MinIO local services
packages/planner/                pure deterministic Python package
apps/api/                        FastAPI process
apps/worker/                     background process
apps/web/                        Next.js App Router application
.github/workflows/ci.yml         clean-checkout verification
```

### Task P0-T01: Pin root toolchain and workspace contracts

**Files:**
- Create: `tests/handoff/test_root_contract.py`
- Create: `.python-version`
- Create: `.node-version`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.editorconfig`
- Create: `.gitignore`
- Create: `.env.example`

**Interfaces:**
- Consumes: approved runtime policy from `engineering-standards.md`
- Produces: root files that pin Python, Node, pnpm and define stable make targets

- [x] **Step 1: Write the failing test**

```python
from pathlib import Path

REQUIRED = {
    ".python-version": "3.13",
    ".node-version": "24",
    "package.json": '"packageManager"',
    "pyproject.toml": "[tool.uv.workspace]",
    "Makefile": "verify:",
}

def test_root_contract_files_and_markers_exist() -> None:
    for name, marker in REQUIRED.items():
        text = Path(name).read_text(encoding="utf-8")
        assert marker in text, (name, marker)
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
python3 -m pytest tests/handoff/test_root_contract.py -q
```

Expected: FAIL because the root toolchain files do not exist.

- [x] **Step 3: Implement the minimum contract**

```python
# package.json
{
  "name": "personal-pm-agent",
  "private": true,
  "packageManager": "pnpm@10.34.0",
  "engines": {"node": ">=24 <25"},
  "scripts": {
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck",
    "test": "pnpm -r test",
    "build": "pnpm -r build"
  }
}

# pyproject.toml
[tool.uv.workspace]
members = ["packages/planner", "apps/api", "apps/worker"]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.mypy]
python_version = "3.13"
strict = true
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
python3 -m pytest tests/handoff/test_root_contract.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
python3 scripts/verify_package.py && git diff --check
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add tests/handoff/test_root_contract.py .python-version .node-version package.json pnpm-workspace.yaml pyproject.toml Makefile .editorconfig .gitignore .env.example
git commit -m "chore(repo): pin toolchain and workspace contracts"
```

### Task P0-T02: Create local infrastructure contract

**Files:**
- Create: `tests/handoff/test_compose_contract.py`
- Create: `compose.yaml`
- Create: `infra/docker/postgres/init.sql`
- Create: `infra/docker/minio/create-bucket.sh`

**Interfaces:**
- Consumes: environment variable names from `.env.example`
- Produces: healthy PostgreSQL, Redis and S3-compatible services with persistent local volumes

- [x] **Step 1: Write the failing test**

```python
from pathlib import Path
import yaml

def test_compose_declares_required_services_and_healthchecks() -> None:
    data = yaml.safe_load(Path("compose.yaml").read_text())
    assert {"postgres", "redis", "minio"} <= set(data["services"])
    for service in ("postgres", "redis", "minio"):
        assert "healthcheck" in data["services"][service]
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
python3 -m pytest tests/handoff/test_compose_contract.py -q
```

Expected: FAIL because `compose.yaml` is absent.

- [x] **Step 3: Implement the minimum contract**

```python
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_DB: personal_pm
      POSTGRES_USER: personal_pm
      POSTGRES_PASSWORD: local_only_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U personal_pm -d personal_pm"]
      interval: 5s
      timeout: 3s
      retries: 20
  redis:
    image: redis:8
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
  minio:
    image: minio/minio
    command: ["server", "/data", "--console-address", ":9001"]
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 3s
      retries: 20
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
python3 -m pytest tests/handoff/test_compose_contract.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
docker compose -f compose.yaml config >/dev/null
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add tests/handoff/test_compose_contract.py compose.yaml infra/docker/postgres/init.sql infra/docker/minio/create-bucket.sh
git commit -m "chore(infra): define local data services"
```

### Task P0-T03: Bootstrap the pure Planner package

**Files:**
- Create: `packages/planner/pyproject.toml`
- Create: `packages/planner/src/personal_pm_planner/__init__.py`
- Create: `packages/planner/src/personal_pm_planner/version.py`
- Create: `packages/planner/tests/test_package_contract.py`

**Interfaces:**
- Consumes: root uv workspace
- Produces: `personal_pm_planner` import and explicit planner package version with no framework dependencies

- [x] **Step 1: Write the failing test**

```python
from importlib.metadata import version
import personal_pm_planner

def test_planner_package_is_importable_and_versioned() -> None:
    assert personal_pm_planner.__version__ == version("personal-pm-planner")
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run --package personal-pm-planner pytest packages/planner/tests/test_package_contract.py -q
```

Expected: FAIL because the package is not defined.

- [x] **Step 3: Implement the minimum contract**

```python
# packages/planner/src/personal_pm_planner/version.py
from importlib.metadata import version

__version__ = version("personal-pm-planner")

# packages/planner/src/personal_pm_planner/__init__.py
from .version import __version__

__all__ = ["__version__"]
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run --package personal-pm-planner pytest packages/planner/tests/test_package_contract.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run ruff check packages/planner && uv run mypy packages/planner/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add packages/planner/pyproject.toml packages/planner/src/personal_pm_planner/__init__.py packages/planner/src/personal_pm_planner/version.py packages/planner/tests/test_package_contract.py
git commit -m "chore(planner): bootstrap pure Python package"
```

### Task P0-T04: Bootstrap FastAPI settings and health endpoints

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/personal_pm_api/__init__.py`
- Create: `apps/api/src/personal_pm_api/settings.py`
- Create: `apps/api/src/personal_pm_api/main.py`
- Create: `apps/api/tests/test_health.py`

**Interfaces:**
- Consumes: root uv workspace and environment contract
- Produces: `create_app()` and `/health/live`, `/health/ready` endpoints

- [x] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from personal_pm_api.main import create_app

def test_live_health_is_process_only() -> None:
    response = TestClient(create_app()).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run --package personal-pm-api pytest apps/api/tests/test_health.py -q
```

Expected: FAIL because `create_app` does not exist.

- [x] **Step 3: Implement the minimum contract**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Personal PM Agent API", version="0.1.0")

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run --package personal-pm-api pytest apps/api/tests/test_health.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run ruff check apps/api && uv run mypy apps/api/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/pyproject.toml apps/api/src/personal_pm_api/__init__.py apps/api/src/personal_pm_api/settings.py apps/api/src/personal_pm_api/main.py apps/api/tests/test_health.py
git commit -m "chore(api): bootstrap FastAPI application"
```

### Task P0-T05: Bootstrap the worker process contract

**Files:**
- Create: `apps/worker/pyproject.toml`
- Create: `apps/worker/src/personal_pm_worker/__init__.py`
- Create: `apps/worker/src/personal_pm_worker/main.py`
- Create: `apps/worker/tests/test_worker_contract.py`

**Interfaces:**
- Consumes: root uv workspace
- Produces: a worker entrypoint that validates settings and exposes a deterministic startup result

- [x] **Step 1: Write the failing test**

```python
from personal_pm_worker.main import build_worker_identity

def test_worker_identity_is_stable() -> None:
    assert build_worker_identity("local") == "personal-pm-worker:local"
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
uv run --package personal-pm-worker pytest apps/worker/tests/test_worker_contract.py -q
```

Expected: FAIL because the worker package does not exist.

- [x] **Step 3: Implement the minimum contract**

```python
def build_worker_identity(environment: str) -> str:
    normalized = environment.strip().lower()
    if not normalized:
        raise ValueError("environment must not be empty")
    return f"personal-pm-worker:{normalized}"
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
uv run --package personal-pm-worker pytest apps/worker/tests/test_worker_contract.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
uv run ruff check apps/worker && uv run mypy apps/worker/src
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/pyproject.toml apps/worker/src/personal_pm_worker/__init__.py apps/worker/src/personal_pm_worker/main.py apps/worker/tests/test_worker_contract.py
git commit -m "chore(worker): bootstrap worker process"
```

### Task P0-T06: Bootstrap Next.js App Router and test baseline

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/test/home.test.tsx`

**Interfaces:**
- Consumes: root pnpm workspace
- Produces: strict TypeScript Next.js app with a render test and production build

- [x] **Step 1: Write the failing test**

```python
// apps/web/src/test/home.test.tsx
import { render, screen } from "@testing-library/react";
import HomePage from "../app/page";

it("renders the product identity", () => {
  render(<HomePage />);
  expect(screen.getByRole("heading", { name: "Personal PM Agent" })).toBeVisible();
});
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
pnpm --filter @personal-pm/web test -- --run
```

Expected: FAIL because the web workspace and page are absent.

- [x] **Step 3: Implement the minimum contract**

```python
// apps/web/src/app/page.tsx
export default function HomePage() {
  return (
    <main>
      <h1>Personal PM Agent</h1>
      <p>계획을 세우는 것이 아니라 유지하고 재조정합니다.</p>
    </main>
  );
}
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
pnpm --filter @personal-pm/web test -- --run
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
pnpm --filter @personal-pm/web typecheck && pnpm --filter @personal-pm/web build
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add apps/web/package.json apps/web/tsconfig.json apps/web/next.config.ts apps/web/src/app/layout.tsx apps/web/src/app/page.tsx apps/web/src/test/home.test.tsx
git commit -m "chore(web): bootstrap Next.js application"
```

### Task P0-T07: Create unified quality commands and CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.pre-commit-config.yaml`
- Create: `scripts/verify_repo.py`
- Modify: `Makefile`
- Create: `tests/handoff/test_command_contract.py`

**Interfaces:**
- Consumes: all bootstrapped workspaces
- Produces: `make verify` and a CI workflow that run format, lint, type, test and build from a clean checkout

- [x] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_makefile_exposes_required_targets() -> None:
    text = Path("Makefile").read_text()
    for target in ("format-check:", "lint:", "typecheck:", "test-unit:", "build:", "verify:"):
        assert target in text
```

- [x] **Step 2: Run the focused test and confirm the intended failure**

Run:

```bash
python3 -m pytest tests/handoff/test_command_contract.py -q
```

Expected: FAIL because the unified targets and CI are incomplete.

- [x] **Step 3: Implement the minimum contract**

```python
# Makefile excerpt
.PHONY: format-check lint typecheck test-unit build verify

format-check:
	uv run ruff format --check apps packages
	pnpm -r format:check

lint:
	uv run ruff check apps packages
	pnpm -r lint

typecheck:
	uv run mypy apps/api/src apps/worker/src packages/planner/src
	pnpm -r typecheck

test-unit:
	uv run pytest -m "not integration and not e2e"
	pnpm -r test -- --run

build:
	pnpm -r build

verify: format-check lint typecheck test-unit build
```

- [x] **Step 4: Run the focused test and confirm it passes**

```bash
python3 -m pytest tests/handoff/test_command_contract.py -q
```

Expected: PASS with zero failures.

- [x] **Step 5: Run adjacent verification**

```bash
make verify && git diff --check
```

- [x] **Step 6: Commit the reviewable unit**

```bash
git add .github/workflows/ci.yml .pre-commit-config.yaml scripts/verify_repo.py Makefile tests/handoff/test_command_contract.py
git commit -m "ci(repo): enforce clean-checkout verification"
```

## Phase 0 Exit Criteria

- [x] A clean clone can install dependencies using committed lockfiles.
- [x] Local PostgreSQL, Redis and object storage report healthy.
- [x] Planner, API, worker and web tests run independently.
- [x] `make verify` succeeds locally and in CI.
- [x] No product behavior beyond bootstraps is implemented.
- [x] `IMPLEMENTATION_STATUS.md` advances to Phase 1.
