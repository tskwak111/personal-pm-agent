# Personal PM Agent — Final Development Package Manifest

## 1. 패키지 요약

이 패키지는 승인된 Personal PM Agent를 새 Git 저장소 또는 기존 저장소의 격리된 worktree에서 바로 구현하기 위한 최종 handoff다.

```text
승인 명세                     3개
구현 Phase                    9개
TDD Task                     77개
추적 요구사항                104개
제품 인수 시나리오            20개
Evaluation Metric ID          64개
Codex 실행·재개·리뷰 프롬프트   7개
```

## 2. 시작 파일

| 순서 | 파일 | 역할 |
|---:|---|---|
| 1 | `00_START_HERE.md` | 복사·검증·읽기·실행 순서 |
| 2 | `AGENTS.md` | 모든 코딩 에이전트의 지속 규칙 |
| 3 | `prompts/CODEX_MASTER_META_PROMPT.md` | 첫 Codex 세션 전체 실행 지시 |
| 4 | `docs/status/IMPLEMENTATION_STATUS.md` | 현재 Phase와 첫 미완료 Task |
| 5 | `docs/plans/00-master-implementation-roadmap.md` | 전체 의존성, Interface와 Gate |

## 3. 승인 명세

```text
docs/specs/2026-08-23-personal-pm-agent-design.md
docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md
docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md
```

`SOURCE_SPEC_HASHES.sha256`가 세 원본 명세의 패키지 내 무결성을 검증한다.

## 4. 아키텍처·요구사항·품질 계약

```text
docs/architecture/decision-precedence.md
docs/architecture/domain-state-machines.md
docs/architecture/engineering-standards.md
docs/architecture/repository-and-module-contract.md
docs/architecture/toolchain-baseline.md

docs/requirements/requirements-traceability.md
docs/requirements/acceptance-scenarios.md

docs/quality/definition-of-done.md
docs/quality/verification-command-matrix.md

docs/operations/security-privacy-and-runbook.md
```

## 5. 단계별 구현계획

| Phase | 계획 | 주요 결과 |
|---:|---|---|
| 0 | `docs/plans/01-phase-0-foundation.md` | 재현 가능한 monorepo, local services, CI |
| 1 | `docs/plans/02-phase-1-domain-core.md` | Planning Core snapshot, state machine, authority |
| 2 | `docs/plans/03-phase-2-planner-engine.md` | 결정론적 Base/Safety Planner와 risk/replanning |
| 3 | `docs/plans/04-phase-3-persistence-api.md` | PostgreSQL, UoW, ownership, API, outbox |
| 4 | `docs/plans/05-phase-4-intake-llm-files.md` | source, inbox, files, LLM, evidence, decomposition |
| 5 | `docs/plans/06-phase-5-calendar-execution.md` | OAuth, sync, Focus Block, idempotent execution |
| 6 | `docs/plans/07-phase-6-agent-briefing.md` | Agent Operations, Approval, Work Session, briefing |
| 7 | `docs/plans/08-phase-7-web-pwa.md` | AI Life Audit와 5개 핵심 Web/PWA 화면 |
| 8 | `docs/plans/09-phase-8-evaluation-security-deployment.md` | Stage A~C, 보안, 관찰성, 배포, 파일럿 |

## 6. 상태·템플릿

```text
docs/status/IMPLEMENTATION_STATUS.md
docs/status/DECISION_LOG.md
docs/status/RISK_REGISTER.md
docs/status/HANDOFF_CHECKLIST.md
docs/status/VERIFICATION_EVIDENCE.md

docs/templates/ADR_TEMPLATE.md
docs/templates/INCIDENT_TEMPLATE.md
docs/templates/RELEASE_REPORT_TEMPLATE.md
docs/templates/TASK_COMPLETION_TEMPLATE.md
```

## 7. Codex 프롬프트

| 파일 | 용도 |
|---|---|
| `prompts/CODEX_MASTER_META_PROMPT.md` | 새 저장소 전체 개발 시작 |
| `prompts/CODEX_PHASE_PROMPTS.md` | 특정 Phase 재개 |
| `prompts/CODEX_RESUME_PROMPT.md` | 중단된 일반 작업 상태 기반 재개 |
| `prompts/CODEX_PHASE_EXECUTION_PROMPT_TEMPLATE.md` | 특정 Task만 격리 실행 |
| `prompts/CODE_REVIEW_PROMPT.md` | Task·Phase 병합 전 엄격 리뷰 |
| `prompts/CODEX_FINAL_AUDIT_META_PROMPT.md` | 전체 구현 완료 주장 후 독립 적대적 감사 |
| `prompts/RELEASE_AUDIT_PROMPT.md` | Release Candidate의 공식 Gate 감사 |

## 8. 검증과 무결성

```bash
python3 scripts/verify_package.py

# 선택적 개별 파일 해시 재검증
sha256sum -c MANIFEST.sha256        # Linux
shasum -a 256 -c MANIFEST.sha256   # macOS
```

패키지 검증기는 다음을 확인한다.

- 필수 파일과 세 원본 명세 hash
- 9개 Phase와 77개 안정 Task ID
- Task별 Files, Interfaces, RED/GREEN, Expected와 Commit 계약
- 104개 요구사항의 Task 추적성과 20개 Gherkin 인수 시나리오
- Markdown fence와 금지 placeholder
- Master Meta-Prompt의 필수 안전·TDD·Skill 지시

`MANIFEST.sha256`는 최종 ZIP에 포함되는 개별 파일의 생성 시점 hash다. 정상 수정 후에는 새 manifest를 생성한다.
