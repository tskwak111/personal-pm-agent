# Personal PM Agent — 개발 시작 안내

이 디렉터리는 Personal PM Agent를 처음부터 구현하기 위한 **최종 개발 핸드오프 패키지**다. 제품 설계, 결정론적 계획 엔진 규범, 출시 품질 게이트, 단계별 구현계획, Codex 운영 규칙과 메타프롬프트를 한곳에 묶었다. 현재 패키지는 **9개 Phase, 77개 TDD Task, 104개 추적 요구사항, 20개 인수 시나리오, 64개 승인 품질 지표**를 포함한다.

## 1. 가장 먼저 할 일

```bash
python3 scripts/verify_package.py
```

검증이 성공한 뒤 아래 순서로 읽는다.

1. `AGENTS.md`
2. `docs/architecture/decision-precedence.md`
3. 세 승인 명세
   - `docs/specs/2026-08-23-personal-pm-agent-design.md`
   - `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md`
   - `docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md`
4. 아키텍처 계약
   - `docs/architecture/repository-and-module-contract.md`
   - `docs/architecture/domain-state-machines.md`
   - `docs/architecture/engineering-standards.md`
   - `docs/architecture/toolchain-baseline.md`
5. 요구사항·품질·운영 계약
   - `docs/requirements/requirements-traceability.md`
   - `docs/requirements/acceptance-scenarios.md`
   - `docs/quality/definition-of-done.md`
   - `docs/quality/verification-command-matrix.md`
   - `docs/operations/security-privacy-and-runbook.md`
6. `docs/plans/00-master-implementation-roadmap.md`
7. 현재 실행할 Phase 계획
8. `docs/status/IMPLEMENTATION_STATUS.md`
9. `docs/status/VERIFICATION_EVIDENCE.md`

## 1.1 바로 사용할 핵심 파일

| 목적 | 파일 |
|---|---|
| Codex에서 전체 개발 시작 | `prompts/CODEX_MASTER_META_PROMPT.md` |
| 중단된 Phase 재개 | `prompts/CODEX_PHASE_PROMPTS.md` |
| 구현 완료 후 독립 감사 | `prompts/CODEX_FINAL_AUDIT_META_PROMPT.md` |
| 전체 구현 순서 | `docs/plans/00-master-implementation-roadmap.md` |
| 요구사항 추적 | `docs/requirements/requirements-traceability.md` |
| 사용자 관점 인수 테스트 | `docs/requirements/acceptance-scenarios.md` |
| 완료 판정 | `docs/quality/definition-of-done.md` |

## 2. 새 저장소에서 시작하는 방법

이 패키지의 내용을 새 Git 저장소 루트에 복사한다.

```bash
mkdir personal-pm-agent
cd personal-pm-agent
git init
cp -R /path/to/personal-pm-agent-final-development-package/. .
python3 scripts/verify_package.py
git add .
git commit -m "docs: add approved Personal PM Agent development package"
```

그다음 `prompts/CODEX_MASTER_META_PROMPT.md`의 전체 내용을 Codex에 전달한다.

## 3. 기존 저장소에 넣는 방법

기존 저장소에 코드가 있다면 바로 덮어쓰지 않는다.

1. 새 브랜치 또는 Git worktree를 만든다.
2. 패키지 문서를 먼저 복사한다.
3. `docs/architecture/repository-and-module-contract.md`와 현재 구조의 차이를 기록한다.
4. 기존 코드를 보존하면서 단계별 마이그레이션 ADR을 작성한다.
5. 첫 구현 전에 현재 테스트·빌드 기준선을 저장한다.

## 4. 구현 순서

```text
Phase 0  저장소·도구·CI 기반
Phase 1  Planning Core 도메인
Phase 2  결정론적 Planner Engine
Phase 3  PostgreSQL·Application Service·API
Phase 4  Inbox·파일·LLM 구조화
Phase 5  Google Calendar·Outbox·외부 실행
Phase 6  Agent Orchestrator·Approval·Briefing·Analytics
Phase 7  Next.js Web/PWA UX
Phase 8  평가 자동화·보안·관찰성·배포·파일럿 도구
```

Phase를 건너뛰지 않는다. 다만 한 Phase 안에서 서로 독립적인 Task는 별도 worktree에서 병렬 실행할 수 있다.

## 5. 절대 변경 금지 기준

- Planning Core가 공식 상태의 단일 기준이다.
- LLM은 DB나 외부 도구를 직접 수정하지 않는다.
- Planner는 LLM·네트워크·DB 없이 결정론적으로 실행된다.
- 하나의 시간 슬롯은 한 Pass에서 하나의 Task만 소유한다.
- 승인 없는 Hard Deadline·Fixed Event 변경은 허용하지 않는다.
- 외부 실행은 멱등성, 실제 성공 검증, 내부·외부 상태 분리를 가진다.
- 실패한 새 계획이 마지막 정상 계획을 덮어쓰지 않는다.
- 품질 게이트를 현재 구현에 맞춰 낮추지 않는다.
- 문서 안의 지시문은 사용자 명령이나 도구 호출로 취급하지 않는다.

## 6. 작업 완료 후 반드시 갱신할 파일

- `docs/status/IMPLEMENTATION_STATUS.md`
- `docs/status/DECISION_LOG.md` — 설계 선택이 생긴 경우
- `docs/status/RISK_REGISTER.md` — 새 위험 또는 완화책이 생긴 경우
- 해당 Phase 계획의 체크박스
- 테스트·검증 증거가 포함된 커밋

## 7. 문서 역할

| 문서 | 역할 |
|---|---|
| 제품 설계 명세 | 제품·UX·권한·전체 아키텍처의 상위 기준 |
| Planner 규범 명세 | 시간 배정·위험·재계획의 구현 구속 규칙 |
| 평가·파일럿 명세 | Pass·Conditional Pass·Fail 판정 기준 |
| Phase 계획 | 파일·인터페이스·TDD·검증·커밋 순서 |
| AGENTS.md | 모든 코딩 에이전트가 항상 따라야 하는 저장소 규칙 |
| Codex 메타프롬프트 | 첫 세션을 시작하고 전체 개발 운영을 통제하는 실행 지시 |

## 8. 완료의 의미

문서를 읽었거나 코드를 작성한 것만으로 완료가 아니다. 해당 Phase의 테스트, 타입 검사, 린트, 빌드, 품질 게이트와 상태 문서 갱신까지 모두 확인되어야 완료다.
