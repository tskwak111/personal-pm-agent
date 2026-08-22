# Phase 4 — Inbox, File Processing and LLM Structuring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept natural language, files and images into a source-preserving inbox; extract structured candidates through a provider-independent LLM Gateway; score evidence and safely auto-register only low-harm, high-confidence facts.

**Architecture:** Upload and extraction jobs preserve immutable source artifacts. Parsers and LLM adapters return candidates with source references; application policies validate schema, dates, duplicates, conflicts, evidence and expected harm before creating Planning Core commands.

**Tech Stack:** FastAPI uploads, S3-compatible storage, Redis-backed worker, deterministic parser ports, Pydantic structured schemas, provider adapters, fake LLM, pytest and golden dataset tools.

**Spec:** Design sections 9, 10, 20 and 22; Evaluation AI-001 through AI-015.

## Global Constraints

- Follow `AGENTS.md` and `docs/architecture/decision-precedence.md`.
- Never weaken Planner or Evaluation gates.
- Use TDD: failing test, confirmed failure, minimum implementation, focused pass, adjacent regression, commit.
- Every state change verifies workspace ownership and expected object version.
- External behavior is represented by ports and deterministic fakes in unit tests.
- Update `docs/status/IMPLEMENTATION_STATUS.md` after every completed Task.
- Do not claim completion without fresh command output.

---

## Locked File Map

```text
apps/api/src/personal_pm_api/inbox/
├─ models.py
├─ schemas.py
├─ repository.py
├─ service.py
├─ evidence.py
├─ registration_policy.py
└─ router.py
apps/worker/src/personal_pm_worker/files/
├─ storage.py
├─ parsers.py
├─ pipeline.py
└─ jobs.py
apps/worker/src/personal_pm_worker/llm/
├─ gateway.py
├─ prompts.py
├─ schemas.py
├─ adapters/
└─ fake.py
prompts/runtime/
evals/golden/
```

### Task P4-T01: Persist source artifacts and safe upload metadata

**Files:**
- Create: `apps/api/src/personal_pm_api/inbox/models.py`
- Create: `apps/api/src/personal_pm_api/inbox/schemas.py`
- Create: `apps/api/src/personal_pm_api/inbox/repository.py`
- Create: `apps/api/src/personal_pm_api/inbox/router.py`
- Create: `apps/api/tests/integration/test_source_upload.py`

**Interfaces:**
- Consumes: workspace ownership, object storage configuration and outbox
- Produces: upload initiation/completion records with checksum, content type, size, storage key and immutable source identity

- [ ] **Step 1: Write the failing test**

```python
def test_upload_rejects_oversized_or_disallowed_file(auth_client) -> None:
    response = auth_client.post("/api/v1/source-artifacts/uploads", json={"filename": "payload.exe", "content_type": "application/x-msdownload", "size_bytes": 10})
    assert response.status_code == 422
    assert response.json()["code"] == "UNSUPPORTED_SOURCE_TYPE"

def test_source_artifact_key_is_workspace_scoped(auth_client) -> None:
    response = auth_client.post("/api/v1/source-artifacts/uploads", json={"filename": "syllabus.pdf", "content_type": "application/pdf", "size_bytes": 1024})
    assert response.status_code == 201
    assert response.json()["storage_key"].startswith("workspaces/")
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_source_upload.py -q
```

Expected: FAIL because source upload records and routes are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_SOURCE_BYTES = 25 * 1024 * 1024

def validate_source_upload(content_type: str, size_bytes: int) -> None:
    if content_type not in ALLOWED_TYPES:
        raise UnsupportedSourceTypeError(content_type)
    if size_bytes <= 0 or size_bytes > MAX_SOURCE_BYTES:
        raise SourceSizeError(size_bytes)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_source_upload.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_identity_and_ownership.py apps/api/tests/integration/test_source_upload.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/inbox/models.py apps/api/src/personal_pm_api/inbox/schemas.py apps/api/src/personal_pm_api/inbox/repository.py apps/api/src/personal_pm_api/inbox/router.py apps/api/tests/integration/test_source_upload.py
git commit -m "feat(inbox): persist safe source artifacts"
```

### Task P4-T02: Implement object storage and parser ports with immutable extraction versions

**Files:**
- Create: `apps/worker/src/personal_pm_worker/files/storage.py`
- Create: `apps/worker/src/personal_pm_worker/files/parsers.py`
- Create: `apps/worker/src/personal_pm_worker/files/pipeline.py`
- Create: `apps/worker/tests/files/test_extraction_pipeline.py`

**Interfaces:**
- Consumes: source artifact records and S3-compatible bucket
- Produces: `ObjectStorage`, `DocumentParser`, `ExtractionResult` and versioned extraction pipeline

- [ ] **Step 1: Write the failing test**

```python
async def test_same_source_and_parser_version_reuses_extraction(pipeline, stored_pdf) -> None:
    first = await pipeline.extract(stored_pdf, parser_version="pdf-v1")
    second = await pipeline.extract(stored_pdf, parser_version="pdf-v1")
    assert second.id == first.id
    assert pipeline.parser_call_count == 1

async def test_extraction_preserves_page_source_locations(pipeline, stored_pdf) -> None:
    result = await pipeline.extract(stored_pdf, parser_version="pdf-v1")
    assert all(chunk.page_number is not None for chunk in result.chunks)
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/files/test_extraction_pipeline.py -q
```

Expected: FAIL because storage and parser ports are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
class DocumentParser(Protocol):
    async def parse(self, content: bytes, content_type: str) -> ExtractionResult: ...

@dataclass(frozen=True, slots=True)
class ExtractionChunk:
    text: str
    page_number: int | None
    block_index: int
    bounding_box: tuple[float, float, float, float] | None
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/files/test_extraction_pipeline.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run ruff check apps/worker && uv run mypy apps/worker/src
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/files/storage.py apps/worker/src/personal_pm_worker/files/parsers.py apps/worker/src/personal_pm_worker/files/pipeline.py apps/worker/tests/files/test_extraction_pipeline.py
git commit -m "feat(files): add versioned extraction pipeline"
```

### Task P4-T03: Implement Inbox lifecycle and processing operations

**Files:**
- Create: `apps/api/src/personal_pm_api/inbox/service.py`
- Create: `apps/worker/src/personal_pm_worker/files/jobs.py`
- Create: `apps/api/tests/integration/test_inbox_lifecycle.py`

**Interfaces:**
- Consumes: source artifact, outbox/job records and extraction pipeline
- Produces: New → Processing → Needs Confirmation/Structured/Ignored/Failed transitions with retry-safe operation IDs

- [ ] **Step 1: Write the failing test**

```python
async def test_processing_failure_preserves_source_and_marks_inbox_failed(inbox_service, failing_job) -> None:
    item = await inbox_service.create_from_text(failing_job.actor, "금요일까지 과제")
    await failing_job.run(item.id)
    reloaded = await inbox_service.get(failing_job.actor, item.id)
    assert reloaded.status == "FAILED"
    assert reloaded.source_artifact_id is not None

async def test_duplicate_job_delivery_does_not_duplicate_candidates(inbox_service, job, inbox_item) -> None:
    await job.run(inbox_item.id)
    await job.run(inbox_item.id)
    assert await count_candidates(inbox_item.id) == 1
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/integration/test_inbox_lifecycle.py -q
```

Expected: FAIL because Inbox operations are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
INBOX_TRANSITIONS = {
    "NEW": {"PROCESSING", "IGNORED"},
    "PROCESSING": {"NEEDS_CONFIRMATION", "STRUCTURED", "FAILED"},
    "NEEDS_CONFIRMATION": {"STRUCTURED", "IGNORED", "PROCESSING"},
    "FAILED": {"PROCESSING", "IGNORED"},
    "STRUCTURED": set(),
    "IGNORED": set(),
}
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/integration/test_inbox_lifecycle.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/integration/test_source_upload.py apps/api/tests/integration/test_inbox_lifecycle.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/inbox/service.py apps/worker/src/personal_pm_worker/files/jobs.py apps/api/tests/integration/test_inbox_lifecycle.py
git commit -m "feat(inbox): implement processing lifecycle"
```

### Task P4-T04: Build provider-independent LLM Gateway and versioned structured prompts

**Files:**
- Create: `apps/worker/src/personal_pm_worker/llm/gateway.py`
- Create: `apps/worker/src/personal_pm_worker/llm/schemas.py`
- Create: `apps/worker/src/personal_pm_worker/llm/prompts.py`
- Create: `apps/worker/src/personal_pm_worker/llm/fake.py`
- Create: `prompts/runtime/intake-structuring-v1.md`
- Create: `prompts/runtime/project-decomposition-v1.md`
- Create: `apps/worker/tests/llm/test_gateway_contract.py`

**Interfaces:**
- Consumes: extracted chunks and operation tracing
- Produces: `LLMGateway.generate_structured()` with prompt/model versions, schema validation, one bounded repair and deterministic fake

- [ ] **Step 1: Write the failing test**

```python
async def test_untrusted_content_is_separate_from_policy(fake_gateway, structured_request) -> None:
    await fake_gateway.generate_structured(structured_request)
    rendered = fake_gateway.last_rendered_request
    assert "UNTRUSTED_SOURCE_CONTENT" in rendered
    assert "SYSTEM_POLICY" in rendered
    assert rendered.index("SYSTEM_POLICY") < rendered.index("UNTRUSTED_SOURCE_CONTENT")

async def test_invalid_first_response_gets_one_repair(fake_gateway, repairable_response) -> None:
    fake_gateway.responses = [repairable_response.invalid, repairable_response.valid]
    result = await fake_gateway.generate_structured(repairable_response.request)
    assert result.repair_count == 1
    assert result.value is not None
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/llm/test_gateway_contract.py -q
```

Expected: FAIL because the Gateway and prompt registry are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class StructuredLLMRequest(Generic[T]):
    task_type: str
    prompt_version: str
    schema: type[T]
    verified_facts: tuple[VerifiedFact, ...]
    user_request: str
    untrusted_source_chunks: tuple[SourceChunk, ...]

class LLMGateway:
    async def generate_structured(self, request: StructuredLLMRequest[T]) -> StructuredLLMResult[T]:
        raw = await self.adapter.complete(render_request(request))
        return validate_or_repair_once(raw, request)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/llm/test_gateway_contract.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/llm -q && uv run mypy apps/worker/src
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/llm/gateway.py apps/worker/src/personal_pm_worker/llm/schemas.py apps/worker/src/personal_pm_worker/llm/prompts.py apps/worker/src/personal_pm_worker/llm/fake.py prompts/runtime/intake-structuring-v1.md prompts/runtime/project-decomposition-v1.md apps/worker/tests/llm/test_gateway_contract.py
git commit -m "feat(llm): add structured provider gateway"
```

### Task P4-T05: Extract source-linked candidates and deterministic evidence scores

**Files:**
- Create: `apps/api/src/personal_pm_api/inbox/evidence.py`
- Create: `apps/worker/src/personal_pm_worker/llm/adapters/intake.py`
- Create: `apps/api/tests/unit/test_evidence_score.py`
- Create: `apps/worker/tests/llm/test_intake_structuring.py`

**Interfaces:**
- Consumes: LLM structured schema and source chunk coordinates
- Produces: `CandidateFact`, `EvidenceScore`, source linkage and ambiguity flags

- [ ] **Step 1: Write the failing test**

```python
def test_llm_self_confidence_cannot_produce_high_evidence_alone(candidate_factory) -> None:
    candidate = candidate_factory(model_confidence=0.99, explicit_date=False, source_span=None)
    score = calculate_evidence_score(candidate)
    assert score.value < 0.65
    assert "MISSING_SOURCE_SPAN" in score.reasons

def test_explicit_date_parser_and_two_sources_raise_evidence(candidate_factory) -> None:
    candidate = candidate_factory(explicit_date=True, deterministic_parse=True, agreeing_sources=2)
    score = calculate_evidence_score(candidate)
    assert score.value >= 0.90
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_evidence_score.py apps/worker/tests/llm/test_intake_structuring.py -q
```

Expected: FAIL because candidate evidence is not calculated.

- [ ] **Step 3: Implement the minimum contract**

```python
def calculate_evidence_score(candidate: CandidateFact) -> EvidenceScore:
    points = 0.0
    reasons: list[str] = []
    if candidate.explicit_date:
        points += 0.25
    if candidate.deterministic_parse:
        points += 0.25
    if candidate.source_span is not None:
        points += 0.20
    else:
        reasons.append("MISSING_SOURCE_SPAN")
    if candidate.agreeing_sources >= 2:
        points += 0.20
    if candidate.has_conflict:
        points -= 0.50
        reasons.append("SOURCE_CONFLICT")
    return EvidenceScore(value=max(0.0, min(1.0, points)), reasons=tuple(reasons))
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_evidence_score.py apps/worker/tests/llm/test_intake_structuring.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit apps/worker/tests/llm -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/inbox/evidence.py apps/worker/src/personal_pm_worker/llm/adapters/intake.py apps/api/tests/unit/test_evidence_score.py apps/worker/tests/llm/test_intake_structuring.py
git commit -m "feat(inbox): score source-backed evidence"
```

### Task P4-T06: Implement expected-harm auto-registration policy and conflict checks

**Files:**
- Create: `apps/api/src/personal_pm_api/inbox/registration_policy.py`
- Create: `apps/api/tests/unit/test_registration_policy.py`
- Create: `apps/api/tests/integration/test_candidate_registration.py`

**Interfaces:**
- Consumes: candidate evidence, authorization policy and duplicate/conflict repository queries
- Produces: `decide_registration()` returning Auto, Temporary, Needs Confirmation or Hold

- [ ] **Step 1: Write the failing test**

```python
from personal_pm_api.inbox.registration_policy import decide_registration

def test_hard_deadline_with_unknown_time_requires_confirmation(candidate_factory) -> None:
    decision = decide_registration(candidate_factory(kind="HARD_DEADLINE", evidence=0.99, time_known=False, expected_harm="HIGH"))
    assert decision.action == "NEEDS_CONFIRMATION"

def test_low_harm_note_with_high_evidence_can_auto_register(candidate_factory) -> None:
    decision = decide_registration(candidate_factory(kind="REFERENCE_NOTE", evidence=0.95, expected_harm="LOW"))
    assert decision.action == "AUTO_REGISTER"
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/api/tests/unit/test_registration_policy.py apps/api/tests/integration/test_candidate_registration.py -q
```

Expected: FAIL because automation policy is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def decide_registration(candidate: CandidateFact) -> RegistrationDecision:
    if candidate.has_conflict:
        return RegistrationDecision("NEEDS_CONFIRMATION", "SOURCE_CONFLICT")
    if candidate.kind in {"HARD_DEADLINE", "FIXED_EVENT"} and not candidate.time_known:
        return RegistrationDecision("NEEDS_CONFIRMATION", "TIME_UNKNOWN")
    if candidate.expected_harm == "HIGH":
        return RegistrationDecision("NEEDS_CONFIRMATION", "HIGH_EXPECTED_HARM")
    if candidate.evidence_score >= 0.90 and candidate.expected_harm == "LOW":
        return RegistrationDecision("AUTO_REGISTER", "HIGH_EVIDENCE_LOW_HARM")
    if candidate.evidence_score >= 0.65:
        return RegistrationDecision("TEMPORARY", "MEDIUM_EVIDENCE")
    return RegistrationDecision("HOLD", "LOW_EVIDENCE")
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/api/tests/unit/test_registration_policy.py apps/api/tests/integration/test_candidate_registration.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/api/tests/unit apps/api/tests/integration/test_inbox_lifecycle.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/api/src/personal_pm_api/inbox/registration_policy.py apps/api/tests/unit/test_registration_policy.py apps/api/tests/integration/test_candidate_registration.py
git commit -m "feat(inbox): enforce safe registration policy"
```

### Task P4-T07: Implement approved project decomposition into executable Task candidates

**Files:**
- Create: `apps/worker/src/personal_pm_worker/llm/adapters/decomposition.py`
- Create: `apps/api/src/personal_pm_api/inbox/decomposition_service.py`
- Create: `apps/worker/tests/llm/test_decomposition.py`
- Create: `apps/api/tests/integration/test_decomposition_approval.py`

**Interfaces:**
- Consumes: approved milestone scope, LLM Gateway and Task candidate schemas
- Produces: 30–120 minute Task proposals with dependencies, outputs, completion conditions and approval-bound scope

- [ ] **Step 1: Write the failing test**

```python
async def test_decomposition_rejects_task_without_completion_condition(decomposition_worker, approved_scope) -> None:
    result = await decomposition_worker.decompose(approved_scope)
    assert all(task.completion_conditions for task in result.tasks)

async def test_decomposition_cannot_expand_approved_deliverable(decomposition_service, approved_scope, expanding_result) -> None:
    with pytest.raises(ScopeExpansionError):
        await decomposition_service.accept(approved_scope.actor, expanding_result)
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/llm/test_decomposition.py apps/api/tests/integration/test_decomposition_approval.py -q
```

Expected: FAIL because decomposition validation is absent.

- [ ] **Step 3: Implement the minimum contract**

```python
def validate_decomposition(scope: ApprovedMilestoneScope, result: DecompositionResult) -> None:
    if result.deliverable != scope.deliverable:
        raise ScopeExpansionError()
    for task in result.tasks:
        if not 30 <= task.base_duration_minutes <= 120:
            raise InvalidTaskSizeError(task.title)
        if not task.completion_conditions:
            raise MissingCompletionConditionError(task.title)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/llm/test_decomposition.py apps/api/tests/integration/test_decomposition_approval.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run pytest apps/worker/tests/llm apps/api/tests/integration/test_candidate_registration.py -q
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add apps/worker/src/personal_pm_worker/llm/adapters/decomposition.py apps/api/src/personal_pm_api/inbox/decomposition_service.py apps/worker/tests/llm/test_decomposition.py apps/api/tests/integration/test_decomposition_approval.py
git commit -m "feat(inbox): decompose approved milestones safely"
```

### Task P4-T08: Create golden dataset runner and AI metric outputs

**Files:**
- Create: `evals/golden/README.md`
- Create: `evals/golden/schema/source_case.schema.json`
- Create: `evals/golden/fixtures/sample-cases.jsonl`
- Create: `scripts/run_intake_eval.py`
- Create: `apps/worker/tests/evals/test_golden_runner.py`

**Interfaces:**
- Consumes: LLM fake/provider gateway, extraction pipeline and Evaluation Metric IDs
- Produces: versioned JSONL evaluation runner reporting AI-001 through AI-015 numerators and denominators

- [ ] **Step 1: Write the failing test**

```python
from scripts.run_intake_eval import evaluate_cases

def test_eval_runner_counts_failed_cases_in_denominator(sample_eval_cases) -> None:
    report = evaluate_cases(sample_eval_cases)
    assert report.metrics["AI-001"].denominator == len(sample_eval_cases)

def test_report_separates_first_pass_and_repaired_success(sample_eval_cases) -> None:
    report = evaluate_cases(sample_eval_cases)
    assert report.metrics["AI-001"].numerator <= report.metrics["AI-002"].numerator
```

- [ ] **Step 2: Run the focused test and confirm the intended failure**

```bash
uv run pytest apps/worker/tests/evals/test_golden_runner.py -q
```

Expected: FAIL because the evaluator and schema are absent.

- [ ] **Step 3: Implement the minimum contract**

```python
@dataclass(frozen=True, slots=True)
class MetricCount:
    numerator: int
    denominator: int

    @property
    def rate(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0

def evaluate_cases(cases: Sequence[GoldenCase]) -> EvaluationReport:
    outcomes = [evaluate_case(case) for case in cases]
    return build_metric_report(outcomes, metric_ids=AI_METRIC_IDS)
```

- [ ] **Step 4: Run the focused test and confirm it passes**

```bash
uv run pytest apps/worker/tests/evals/test_golden_runner.py -q
```

Expected: PASS with zero failures.

- [ ] **Step 5: Run adjacent verification**

```bash
uv run python scripts/run_intake_eval.py --dataset evals/golden/fixtures/sample-cases.jsonl --output evals/reports/intake-sample.json
```

- [ ] **Step 6: Commit the reviewable unit**

```bash
git add evals/golden/README.md evals/golden/schema/source_case.schema.json evals/golden/fixtures/sample-cases.jsonl scripts/run_intake_eval.py apps/worker/tests/evals/test_golden_runner.py
git commit -m "test(evals): add intake golden dataset runner"
```

## Phase 4 Exit Criteria

- [ ] Original source, extraction and structured candidates are separately versioned.
- [ ] Duplicate job delivery does not duplicate candidates or Task records.
- [ ] LLM response cannot mutate Planning Core without application validation.
- [ ] Every auto-registered deadline/event has a source span and policy decision.
- [ ] Unknown time and source conflicts always require confirmation.
- [ ] Decomposition cannot silently expand approved milestone scope.
- [ ] AI metric runner reports fixed denominators and first-pass/repair outcomes separately.
