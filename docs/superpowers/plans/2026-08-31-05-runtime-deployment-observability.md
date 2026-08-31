# Runtime, Deployment, and Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make API, worker, web, deployment, and monitoring artifacts runnable and honestly verifiable.

**Architecture:** Each process owns one executable entry point and declares its runtime dependencies. Deployment files are rendered from explicit image digests, statically validated without a cluster, and smoke-tested where local runtimes exist.

**Tech Stack:** uv, Python 3.13, Node 24, Next standalone, Docker, Kubernetes YAML, PostgreSQL, Prometheus-compatible rules

**Spec:** `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md`

## Global Constraints

- Runtime packages declare every imported workspace and third-party dependency.
- API does not run migrations at startup.
- Processes run as non-root and terminate gracefully.
- Deployment never uses `latest`; release rendering requires immutable digests.
- Unavailable Docker, registry, cluster, or managed backup evidence is `BLOCKED_EXTERNAL`.

---

### Task 1: Declare package dependencies and run a real worker loop

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/worker/pyproject.toml`
- Modify: `uv.lock`
- Modify: `apps/worker/src/personal_pm_worker/main.py`
- Create: `apps/worker/src/personal_pm_worker/outbox_worker.py`
- Create: `apps/worker/tests/test_outbox_worker.py`
- Modify: `apps/worker/tests/test_worker_contract.py`

**Interfaces:**
- Produces: `run_once(session_factory, executor, batch_size) -> WorkerRunResult`
- Produces: `python -m personal_pm_worker.main` polling loop with SIGTERM stop

- [x] **Step 1: Write the worker behavior tests**

```python
async def test_run_once_processes_pending_outbox_and_counts_failures() -> None:
    result = await run_once(factory, executor, batch_size=10)
    assert result.claimed == 2
    assert result.succeeded == 1
    assert result.failed == 1

async def test_run_once_without_executor_fails_closed() -> None:
    result = await run_once(factory, None, batch_size=10)
    assert result.succeeded == 0
    assert result.failed == result.claimed
```

- [x] **Step 2: Confirm RED**

Run: `uv run pytest apps/worker/tests/test_outbox_worker.py -q`

- [x] **Step 3: Declare actual imports**

Add `personal-pm-planner` to API dependencies. Add `personal-pm-api`, SQLAlchemy async, asyncpg, and pydantic-settings to worker dependencies, using uv workspace sources at the root. Regenerate `uv.lock`.

- [x] **Step 4: Implement one polling owner**

`outbox_worker.py` selects a bounded pending batch through the existing `OutboxRepository`, executes each item through the existing calendar executor, persists verified status, and commits each idempotent outcome. `main.py` reads settings, installs SIGINT/SIGTERM handlers, and waits with `asyncio.Event.wait()` plus timeout; it does not busy-loop.

- [x] **Step 5: Verify and commit**

```bash
uv lock
uv sync --frozen
uv run pytest apps/worker/tests apps/api/tests/integration/test_outbox_atomicity.py -q
uv run mypy apps/worker/src apps/api/src
git add apps/api/pyproject.toml apps/worker/pyproject.toml uv.lock apps/worker/src apps/worker/tests
git commit -m "feat(worker): execute pending outbox jobs"
```

### Task 2: Build artifacts matching their runtime commands

**Files:**
- Modify: `apps/web/next.config.ts`
- Modify: `infra/docker/Dockerfile.api`
- Modify: `infra/docker/Dockerfile.worker`
- Modify: `infra/docker/Dockerfile.web`
- Modify: `.dockerignore`
- Modify: `apps/api/tests/evals/test_deployment_contract.py`

**Interfaces:**
- Produces: API image with planner package installed
- Produces: worker image with API models and worker package installed
- Produces: web `.next/standalone/apps/web/server.js`

- [x] **Step 1: Write file-contract tests**

```python
def test_web_build_mode_matches_docker_copy() -> None:
    assert 'output: "standalone"' in Path("apps/web/next.config.ts").read_text()
    assert ".next/standalone" in Path("infra/docker/Dockerfile.web").read_text()

def test_worker_image_copies_api_and_worker_sources() -> None:
    source = Path("infra/docker/Dockerfile.worker").read_text()
    assert "COPY apps/api" in source
    assert "COPY apps/worker" in source
```

- [x] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_deployment_contract.py -q`

- [x] **Step 3: Align builds**

Set `output: "standalone"`. Build Python wheels in the builder stage with the locked workspace, copy only the virtual environment and required migration/source assets, and use `python -m ...` commands. Add `HEALTHCHECK` only where the image contains a local health endpoint; Kubernetes probes remain authoritative.

- [x] **Step 4: Verify local artifacts**

```bash
make build
test -f apps/web/.next/standalone/apps/web/server.js
docker build --check -f infra/docker/Dockerfile.api .
docker build --check -f infra/docker/Dockerfile.worker .
docker build --check -f infra/docker/Dockerfile.web .
```

If actual image builds require unavailable network or daemon access, record `BLOCKED_EXTERNAL`; do not replace them with a passing echo.

- [x] **Step 5: Commit**

```bash
git add apps/web/next.config.ts infra/docker .dockerignore apps/api/tests/evals/test_deployment_contract.py
git commit -m "chore(images): align production build artifacts"
```

### Task 3: Render valid Kubernetes manifests from immutable digests

**Files:**
- Rename: `infra/deployment/api.yaml` → `infra/deployment/api.yaml.tmpl`
- Rename: `infra/deployment/worker.yaml` → `infra/deployment/worker.yaml.tmpl`
- Rename: `infra/deployment/web.yaml` → `infra/deployment/web.yaml.tmpl`
- Rename: `infra/deployment/migrate.yaml` → `infra/deployment/migrate.yaml.tmpl`
- Create: `scripts/render_deployment.py`
- Modify: `scripts/smoke_deployment.py`
- Modify: `apps/api/tests/evals/test_deployment_contract.py`
- Modify: `docs/operations/release-runbook.md`

**Interfaces:**
- Consumes: three digests matching `sha256:[0-9a-f]{64}`
- Produces: rendered YAML with selectors, matching labels, probes, resources, security context, and immutable images

- [x] **Step 1: Write invalid-template and rendered-contract tests**

```python
def test_render_requires_real_digest(tmp_path) -> None:
    with pytest.raises(ValueError, match="sha256"):
        render_all(api_digest="latest", worker_digest="latest", web_digest="latest", output=tmp_path)

def test_rendered_deployment_selectors_match_pod_labels(rendered) -> None:
    for deployment in rendered.deployments:
        assert deployment["spec"]["selector"]["matchLabels"] == deployment["spec"]["template"]["metadata"]["labels"]
```

- [x] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/evals/test_deployment_contract.py -q`

- [x] **Step 3: Render with strict string replacement**

Templates contain `@@API_IMAGE@@`, `@@WORKER_IMAGE@@`, and `@@WEB_IMAGE@@`. `render_deployment.py` validates digests with `re.fullmatch(r"sha256:[0-9a-f]{64}")`, substitutes full image references, parses all YAML documents, and writes only after successful validation.

- [x] **Step 4: Complete Deployment contracts**

Every Deployment has `spec.selector`, matching pod labels, readiness/liveness probes where applicable, resource requests/limits, `runAsNonRoot`, read-only root filesystem where supported, dropped capabilities, and explicit configuration/secret references. Migration remains a separate Job.

- [x] **Step 5: Verify and commit**

```bash
uv run pytest apps/api/tests/evals/test_deployment_contract.py -q
uv run python scripts/render_deployment.py --api-digest sha256:$(printf '1%.0s' {1..64}) --worker-digest sha256:$(printf '2%.0s' {1..64}) --web-digest sha256:$(printf '3%.0s' {1..64}) --output /tmp/pma-manifests
uv run python scripts/smoke_deployment.py --manifests /tmp/pma-manifests
git add infra/deployment scripts/render_deployment.py scripts/smoke_deployment.py apps/api/tests/evals/test_deployment_contract.py docs/operations/release-runbook.md
git commit -m "chore(deploy): render immutable valid manifests"
```

### Task 4: Connect metrics and validate alert semantics

**Files:**
- Create: `apps/api/src/personal_pm_api/telemetry/metrics.py`
- Modify: `apps/api/src/personal_pm_api/main.py`
- Modify: `apps/api/src/personal_pm_api/planning/service.py`
- Modify: `apps/worker/src/personal_pm_worker/outbox_worker.py`
- Modify: `infra/monitoring/alerts.yaml`
- Modify: `infra/monitoring/dashboards/api.json`
- Modify: `infra/monitoring/dashboards/planner.json`
- Create: `apps/api/tests/unit/test_runtime_metrics.py`

**Interfaces:**
- Produces: bounded-cardinality counters/histograms for API, planner, outbox, external verification, and failures
- Produces: alert queries whose metric names exist in code

- [ ] **Step 1: Write metric-name contract tests**

```python
def test_every_alert_metric_is_registered() -> None:
    referenced = alert_metric_names(Path("infra/monitoring/alerts.yaml"))
    assert referenced <= REGISTERED_METRICS
```

Add a test asserting workspace IDs, task IDs, provider event IDs, and raw error messages cannot be label keys.

- [ ] **Step 2: Confirm RED**

Run: `uv run pytest apps/api/tests/unit/test_runtime_metrics.py -q`

- [ ] **Step 3: Implement stdlib in-process registry**

Use a small locked counter/histogram registry with fixed metric names and fixed label allowlists; expose Prometheus text at `/internal/metrics` behind an operator token. Do not add an observability SDK until an actual collector is selected.

- [ ] **Step 4: Instrument boundaries**

Record API status/duration, planner status/duration, outbox claimed/succeeded/failed, external verification status, and OAuth exchange failures. Keep trace/correlation IDs in logs, not metric labels.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest apps/api/tests/unit/test_runtime_metrics.py apps/api/tests/unit/test_telemetry_events.py apps/worker/tests/test_outbox_worker.py -q
git add apps/api/src/personal_pm_api/telemetry apps/api/src/personal_pm_api/main.py apps/api/src/personal_pm_api/planning/service.py apps/worker/src/personal_pm_worker/outbox_worker.py infra/monitoring apps/api/tests/unit/test_runtime_metrics.py
git commit -m "feat(observability): connect bounded runtime metrics"
```

### Task 5: Record runtime evidence

**Files:**
- Modify: `docs/status/VERIFICATION_EVIDENCE.md`
- Modify: `docs/status/RISK_REGISTER.md`
- Modify: `docs/requirements/requirements-traceability.md`

- [ ] **Step 1: Run available runtime verification**

```bash
uv run python scripts/check_toolchain.py
uv run python scripts/smoke_deployment.py --manifests /tmp/pma-manifests
make build
make typecheck
make test-unit
git diff --check
```

- [ ] **Step 2: Record blocked external evidence**

List actual Docker image build/push, registry digest resolution, cluster apply/rollout, managed backup RPO/RTO, and production metrics scrape as `BLOCKED_EXTERNAL` until their commands run against real infrastructure.

- [ ] **Step 3: Commit**

```bash
git add docs/status/VERIFICATION_EVIDENCE.md docs/status/RISK_REGISTER.md docs/requirements/requirements-traceability.md
git commit -m "docs(runtime): record deployment readiness evidence"
```
