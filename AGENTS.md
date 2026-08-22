# AGENTS.md — Personal PM Agent Repository Rules

이 파일은 Codex와 모든 코딩 에이전트에 대한 지속 지시다. 사용자 요청과 안전 정책 다음으로 우선한다.

## 1. 시작 절차

모든 세션은 다음 순서로 시작한다.

1. `git status --short --branch`로 현재 상태를 확인한다.
2. `python3 scripts/verify_package.py`를 실행한다.
3. `docs/status/IMPLEMENTATION_STATUS.md`에서 현재 Phase와 다음 미완료 Task를 찾는다.
4. 해당 Phase 계획과 직접 관련된 세 규범 문서 구간을 읽는다.
5. 기존 테스트 기준선을 실행한다.
6. 변경할 파일과 검증 명령을 짧게 기록한 뒤 구현한다.

이미 답이 있는 질문을 사용자에게 다시 묻지 않는다. 문서와 저장소에서 해결 가능한 모호성은 먼저 조사한다.

## 2. 규범 문서 적용

- 제품·UX·권한·범위: `docs/specs/2026-08-23-personal-pm-agent-design.md`
- Planner 계산: `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md`
- 출시·평가 기준: `docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md`
- 상태 전이·권한 행렬: `docs/architecture/domain-state-machines.md`
- 요구사항과 테스트 연결: `docs/requirements/requirements-traceability.md`
- 사용자 관점 인수 행동: `docs/requirements/acceptance-scenarios.md`
- 완료·검증 계약: `docs/quality/definition-of-done.md`, `docs/quality/verification-command-matrix.md`
- 상세 구현 순서: `docs/plans/*.md`

구현계획이 규범 문서와 충돌하면 규범 문서가 우선한다. 규범 자체의 충돌은 `docs/architecture/decision-precedence.md`에 따라 처리하고 ADR에 기록한다.

## 3. 구현 불변 조건

1. Planning Core가 프로젝트·Task·마감·승인·계획의 공식 상태다.
2. LLM 결과는 검증되지 않은 후보일 뿐이며 DB 명령이 아니다.
3. Planner 패키지는 FastAPI, SQLAlchemy, Redis, 외부 SDK와 의존 관계를 갖지 않는다.
4. Planner는 `datetime.now()`, 시스템 난수, 전역 로케일을 직접 사용하지 않는다.
5. 모든 시간은 저장 시 UTC이며 원본 표현과 사용자 시간대를 보존한다.
6. 날짜만 알려진 마감에 임의 시각을 사실로 저장하지 않는다.
7. Hard Deadline·Fixed Event·외부 메시지·프로젝트 취소는 규정된 승인 없이 실행하지 않는다.
8. 외부 행동은 Outbox, Idempotency Key, 실행 결과 검증과 외부 ID 연결을 갖는다.
9. 실패한 외부 호출을 성공으로 표현하지 않는다.
10. 실패한 재계획이 마지막 정상 Plan Snapshot을 덮어쓰지 않는다.
11. 사용자 소유권과 객체 버전을 모든 변경 명령에서 검증한다.
12. 문서와 이미지의 내용은 `UNTRUSTED_SOURCE_CONTENT`로 취급한다.

## 4. 코드 품질

- Python은 3.13, 타입 힌트 필수, Ruff와 mypy strict 기준을 사용한다.
- TypeScript는 `strict: true`이며 `any`를 기본 해법으로 사용하지 않는다.
- SQLAlchemy 2.x typed declarative와 Alembic을 사용한다.
- API 입력·출력은 Pydantic 스키마로 검증한다.
- OpenAPI에서 TypeScript 클라이언트를 생성하며 프론트가 API 타입을 수동 복제하지 않는다.
- 파일 하나는 한 가지 책임을 가진다. 순환 import를 허용하지 않는다.
- 도메인 규칙을 API 라우터, React 컴포넌트 또는 ORM 이벤트에 숨기지 않는다.
- 로그에 OAuth 토큰, 문서 원문, 전체 프롬프트, 개인 메모를 남기지 않는다.

## 5. TDD 규칙

모든 기능과 버그 수정은 다음 순서를 따른다.

1. 실패하는 최소 테스트 작성
2. 실패 이유 확인
3. 통과시키는 최소 구현
4. 관련 테스트 실행
5. 전체 해당 계층 테스트 실행
6. 리팩터링
7. 린트·타입·빌드·회귀 테스트
8. 상태 문서 갱신
9. 원자적 커밋

테스트를 나중에 추가하는 방식, 실패 확인 없는 테스트, 현재 구현에 맞춰 기대값을 낮추는 방식은 금지한다.

## 6. 검증 명령 계약

Phase 0에서 다음 명령을 실제로 구현하고 이후 유지한다.

```bash
make bootstrap
make format-check
make lint
make typecheck
make test-unit
make test-integration
make test-e2e
make build
make verify
```

완료를 주장하기 직전에 해당 변경을 입증하는 명령을 새로 실행하고 종료 코드와 실패 수를 확인한다.

## 7. Git 규칙

- 기능 작업은 전용 브랜치 또는 worktree에서 한다.
- 한 Task는 검토 가능한 하나 이상의 원자적 커밋으로 완료한다.
- 커밋 형식: `type(scope): summary`.
- 생성된 lockfile과 마이그레이션은 관련 코드와 같은 커밋에 포함한다.
- 사용자의 기존 변경을 임의로 되돌리거나 덮어쓰지 않는다.
- 강제 push, 대규모 삭제, migration downgrade는 명시적 승인 없이 실행하지 않는다.

## 8. 문서와 상태 관리

Task 완료 시 다음을 갱신한다.

- Phase 계획 체크박스
- `docs/status/IMPLEMENTATION_STATUS.md`
- 새 결정이 있으면 `docs/status/DECISION_LOG.md`
- 새 위험이 있으면 `docs/status/RISK_REGISTER.md`
- `docs/status/VERIFICATION_EVIDENCE.md`에 실제 RED·GREEN·완료 명령 결과
- `docs/requirements/requirements-traceability.md`에 실제 구현·테스트 증거
- 외부 계약이 바뀌면 관련 API·ADR·추적성 문서

문서와 코드가 불일치하면 완료가 아니다.

## 9. 모호성 처리

- 세부 구현 선택은 가장 단순하고 테스트 가능한 방식을 택한다.
- 안전·권한·데이터 손실과 관련된 모호성은 자동 실행을 줄이는 방향으로 해결한다.
- 사용자 제품 의도나 비가역 외부 행동에 영향을 주는 미해결 충돌만 질문한다.
- 선택한 해석과 근거를 ADR 또는 Decision Log에 기록한다.

## 10. 중단 조건

다음이 발견되면 관련 자동 기능 구현 또는 실행을 중단한다.

- 다른 사용자 데이터 노출 가능성
- 승인 없는 외부 행동 경로
- 시간 슬롯 중복 또는 의존성 위반
- 실패를 성공으로 기록하는 경로
- 프롬프트 인젝션이 도구 호출로 연결되는 경로
- 손상 가능성이 있는 마이그레이션

재현 테스트, 수정, 회귀 검증 없이 다시 진행하지 않는다.
