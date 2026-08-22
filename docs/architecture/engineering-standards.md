# 엔지니어링 표준

## 1. 기준 런타임

- Python: 3.13.x
- Node.js: 24 LTS
- pnpm: 10.x 고정 버전
- Next.js: 16.x
- React: 19.2.x의 보안 수정 패치 이상
- FastAPI: 0.141.x minor 범위 고정
- PostgreSQL: 18.x의 최신 minor
- Redis: 8.x의 보안 수정 릴리스

Phase 0에서 실제 패치와 컨테이너 digest를 확인해 lockfile과 도구 파일에 고정한다. minor 업그레이드는 전체 검증 후 별도 커밋으로 수행한다.

## 2. Python

- 패키지 관리: `uv`
- 포맷·린트: Ruff
- 타입 검사: mypy strict
- 테스트: pytest, pytest-asyncio, Hypothesis
- DB 통합 테스트: Testcontainers 또는 동일한 격리 PostgreSQL
- 데이터 모델: 표준 dataclass/enum for Planner, Pydantic for boundaries, SQLAlchemy 2 typed ORM for persistence
- 시간: aware `datetime`, UTC 저장, `zoneinfo.ZoneInfo`
- 예외: 모듈별 typed application/domain error

## 3. TypeScript

- 패키지 관리: pnpm workspace
- TypeScript `strict: true`
- ESLint와 Prettier
- 단위·컴포넌트 테스트: Vitest + Testing Library
- 브라우저 E2E: Playwright
- API 타입: OpenAPI 생성
- 접근성: keyboard navigation, visible focus, semantic HTML, axe 검사

## 4. API

- `/api/v1` 버전 경로를 사용한다.
- 오류 응답은 안정된 `code`, 사용자 메시지, `trace_id`, 선택적 field errors를 가진다.
- mutating command는 필요한 경우 `expected_version`과 `Idempotency-Key`를 받는다.
- 목록 API는 cursor pagination을 기본으로 한다.
- 날짜·시각 필드는 ISO 8601 UTC와 원본 시간대 메타데이터를 구분한다.
- SSE는 operation status와 agent stream에만 사용한다.

## 5. 데이터베이스

- 모든 사용자 소유 테이블에 `workspace_id`가 존재한다.
- 주요 mutable aggregate에 `version`이 존재한다.
- 삭제가 외부 동기화와 관련되면 tombstone 또는 deleted_at을 사용한다.
- migration은 forward-only를 기본으로 하며 파괴적 변경은 expand/migrate/contract 순서를 따른다.
- JSON은 비핵심 메타데이터에만 사용한다.
- timezone-aware timestamp를 사용한다.

## 6. 보안

- Google OAuth는 Authorization Code + PKCE, state, nonce를 검증한다.
- Calendar read와 write 권한은 단계적으로 요청한다.
- refresh token은 application-level encryption과 key rotation을 지원한다.
- HTTP-only, Secure, SameSite cookie와 CSRF 방어를 사용한다.
- 업로드 파일에 크기·형식·악성 콘텐츠 검사를 적용한다.
- 로그와 tracing attribute에서 민감 데이터를 제거한다.
- rate limit은 인증, 파일 업로드, LLM, 외부 실행에 별도 적용한다.

## 7. LLM

- 모든 호출은 Gateway와 versioned prompt registry를 통한다.
- 구조화 응답은 schema validation을 통과해야 한다.
- `model_confidence`, `evidence_score`, `calibrated_probability`, `expected_harm`을 분리한다.
- 테스트에서는 실제 provider 대신 deterministic fake를 기본 사용한다.
- 원본 문서는 `UNTRUSTED_SOURCE_CONTENT` 섹션에만 넣는다.
- LLM이 만든 reason은 Planner `DecisionEvidence` 밖의 근거를 추가할 수 없다.

## 8. 관찰성

모든 요청과 비동기 operation에 `trace_id` 또는 `operation_id`를 연결한다.

기본 구조화 로그 필드:

```text
timestamp
level
service
environment
trace_id
operation_id
workspace_hash
module
event_name
result
latency_ms
error_code
planner_version
prompt_version
model
```

원문, 토큰, 문서 내용, 전체 일정 설명은 기본 로그 필드가 아니다.

## 9. Definition of Done

- 실패 테스트를 먼저 확인했다.
- 구현과 직접 관련된 단위·통합 테스트가 통과한다.
- lint, typecheck, build가 통과한다.
- public contract가 바뀌면 OpenAPI와 생성 client가 갱신되었다.
- migration이 clean DB와 upgrade DB에서 검증되었다.
- 관련 status, ADR, risk, traceability 문서가 갱신되었다.
- 완료 주장 직전에 검증 명령을 새로 실행했다.
