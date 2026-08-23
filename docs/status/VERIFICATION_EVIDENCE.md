# Verification Evidence Log

This file begins empty of implementation claims. Append one section per completed Task using the format below.

## Record format

```text
Task ID:
Commit SHA:
Timestamp UTC:
Focused red command and observed failure:
Focused green command and result:
Adjacent regression command and result:
Completion command and result:
Generated report/artifact paths:
Reviewer:
Residual risk:
```

Package-generation verification is recorded in `PACKAGE_MANIFEST.md`; it does not prove product implementation.

## P0-T01 — Pin root toolchain and workspace contracts

```text
Task ID: P0-T01
Commit SHA: 91fe556
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: uv run --with pytest python -m pytest tests/handoff/test_root_contract.py -q → 1 failed, FileNotFoundError '.python-version'
Focused green command and result: uv run python -m pytest tests/handoff/test_root_contract.py -q → 1 passed
Adjacent regression command and result: python3 scripts/verify_package.py → FAILED로 관측(매니페스트 커버리지가 .git 포함) → DEC-010에 따라 검증기 최소 수정 후 PASSED; git diff --check clean
Completion command and result: 커밋 91fe556에서 focused test 재실행 1 passed, verify_package.py PASSED
Generated report/artifact paths: tests/handoff/test_root_contract.py, MANIFEST.sha256
Reviewer: ox-alpha (self-review of diff vs plan T01 file list)
Residual risk: 없음. 패치 핀은 DEC-011에 기록
```

## P0-T02 — Create local infrastructure contract

```text
Task ID: P0-T02
Commit SHA: 92c34e6
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: uv run python -m pytest tests/handoff/test_compose_contract.py -q → 1 failed, FileNotFoundError 'compose.yaml'
Focused green command and result: 1 passed
Adjacent regression command and result: docker compose config → exit 0
Completion command and result: 헬스 실증은 Phase 종료 시 수행(아래 Phase 0 Exit 기록 참조)
Generated report/artifact paths: compose.yaml, infra/docker/postgres/init.sql, infra/docker/minio/create-bucket.sh
Reviewer: ox-alpha (self-review)
Residual risk: R-011 컨테이너 다이제스트 미핀(DEC-012)
```

## P0-T03 — Bootstrap the pure Planner package

```text
Task ID: P0-T03
Commit SHA: b81e556
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: uv run --package personal-pm-planner pytest ... → workspace member missing pyproject.toml
Focused green command and result: 1 passed
Adjacent regression command and result: uv run ruff check packages/planner → All checks passed; uv run mypy packages/planner/src → no issues in 2 files
Completion command and result: make verify-planner 후속 통합 명령으로도 커버됨(make test-unit 11 passed에 포함)
Generated report/artifact paths: packages/planner/**
Reviewer: ox-alpha (self-review)
Residual risk: 없음
```

## P0-T04 — Bootstrap FastAPI settings and health endpoints

```text
Task ID: P0-T04
Commit SHA: 7bc3c6f
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: ModuleNotFoundError: No module named 'personal_pm_api'
Focused green command and result: 2 passed (/health/live, /health/ready)
Adjacent regression command and result: ruff check apps/api → passed(fix 이후), mypy apps/api/src → no issues in 3 files
Completion command and result: make test-unit 11 passed에 포함, make build 성공
Generated report/artifact paths: apps/api/**
Reviewer: ox-alpha (self-review)
Residual risk: /health/ready는 아직 의존성 점검 없음 — Phase 3에서 DB readiness로 확장 예정
```

## P0-T05 — Bootstrap the worker process contract

```text
Task ID: P0-T05
Commit SHA: f995df2
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: workspace member missing pyproject.toml
Focused green command and result: 2 passed
Adjacent regression command and result: ruff check apps/worker → passed, mypy apps/worker/src → no issues in 2 files
Completion command and result: make test-unit 11 passed에 포함
Generated report/artifact paths: apps/worker/**
Reviewer: ox-alpha (self-review)
Residual risk: 없음. Job 레지스트리는 Phase 5에서 확장
```

## P0-T06 — Bootstrap Next.js App Router and test baseline

```text
Task ID: P0-T06
Commit SHA: a37899c
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: pnpm --filter @personal-pm/web test -- --run → No projects matched the filters
Focused green command and result: Test Files 1 passed, Tests 1 passed
Adjacent regression command and result: pnpm --filter @personal-pm/web typecheck → exit 0; pnpm --filter @personal-pm/web build → static prerender 성공
Completion command and result: make test-unit(웹 포함)과 make build 통과
Generated report/artifact paths: apps/web/**, pnpm-lock.yaml
Reviewer: ox-alpha (self-review). next 16.3.2/react 19.2.8/typescript 5.9.3/vitest 4.1.11은 npm 레지스트리 조회로 확인
Residual risk: ESLint flat-config 전환(eslint-config-next 직접 import)으로 FlatCompat 제거
```

## P0-T07 — Create unified quality commands and CI

```text
Task ID: P0-T07
Commit SHA: 8a390dc
Timestamp UTC: 2026-08-22T20:45Z (recorded after completion)
Focused red command and observed failure: uv run python -m pytest tests/handoff/test_command_contract.py -q → 4 failed(CI/pre-commit/verify_repo 부재, Makefile verify-repo 부재)
Focused green command and result: 4 passed
Adjacent regression command and result: make test-unit → 11 passed(python) + 1 passed(web); focused handoff suite 6 passed
Completion command and result: make verify → format-check/lint/typecheck/test-unit/build/verify-docs/verify-repo 전부 통과(종료 시점 재실행 기록은 아래 Phase 0 Exit)
Generated report/artifact paths: .github/workflows/ci.yml, scripts/verify_repo.py, .pre-commit-config.yaml
Reviewer: ox-alpha (self-review). CI action 태그(checkout v5.1.0, setup-node v4.4.0)와 pre-commit rev(ruff v0.16.4, hooks v6.0.0)는 원격 태그 조회로 검증
Residual risk: CI 실행 자체는 GitHub 원격 저장소 푸시 후 첫 run에서 확정 필요
```

## Phase 0 Exit verification

```text
Task ID: Phase 0 closeout
Commit SHA: (본 문서를 포함하는 커밋)
Timestamp UTC: 2026-08-22T20:45Z
Commands:
  docker compose up -d (POSTGRES_HOST_PORT=15432 등 오버라이드) → postgres/redis/minio 모두 healthy
  docker exec personal-pm-agent-postgres-1 psql -U personal_pm -d personal_pm -c "SELECT version();" → PostgreSQL 18.6
  docker exec personal-pm-agent-redis-1 redis-cli ping → PONG
  make verify → 전 단계 통과
Notes:
  - 호스트 5432가 기존 서비스로 사용 중이어서 compose 호스트 포트를 환경변수로 오버라이드 가능하게 함(DEC-013)
  - PostgreSQL 18 이미지 볼륨 레이아웃 변경(/var/lib/postgresql 마운트) 반영
Reviewer: ox-alpha (self-review)
Residual risk: RISK_REGISTER의 R-011 유지(다이제스트 핀은 P8 전 필수)
```

## Phase 1 — Domain Core closeout

```text
Task ID: P1-T01..P1-T07 (branch phase/01-domain-core)
Commits: 2cd0597, 5a19e90, 01dd7b9, ac39fa5, 3b47b49, cabd3a0, afb90f0, 74c1442
Timestamp UTC: 2026-08-22T21:30Z
Focused red commands and observed failures:
  P1-T01 ModuleNotFoundError personal_pm_planner.domain
  P1-T02 collection error domain.work 부재
  P1-T03 ImportError TaskId 미정의
  P1-T04 import error dependency 모듈 부재
  P1-T05 import error availability/식별자 부재
  P1-T06 import error authorization 부재
  P1-T07 import error PlannerInput 부재
Focused green results:
  P1-T01 5 passed / P1-T02 13 passed(domain) / P1-T03+전수 엣지 59 passed(planner 전체)
  P1-T04 SCC 사이클 안정성 포함 통과 / P1-T05 불변식 테스트 통과
  P1-T06 권한 행렬·승인 바인딩·감사 계약 통과 / P1-T07 순서 무관 canonical 직렬화 통과
Adjacent regression: uv run pytest packages/planner/tests -q → 59 passed; ruff/mypy strict → clean
Completion command: make verify → 전 단계 통과(아래 재실행 기록)
Notes:
  - DEC-014: Ready→Waiting/Blocked 엣지와 Waiting 이탈 사유 해소, CANCELLED 잔여량 영정 의미를 기록
  - 추적표 증거 경로를 tests/domain 실제 레이아웃으로 갱신(문서 규칙상 허용되는 경로 정제)
Residual risk: 없음. Phase 2 참조 벡터에서 도메인 계약 소비 확인 예정

```


## Phase 2 — Planner Engine closeout (T01–T10)

```text
Task ID: P2-T01..P2-T10
Commits: 1ca6e0e, 13cef0f, 0c3d312, 6605cf4, 166ef81/d3853b0, d685f5a, 9eb4f10, 57abc77, d1d518b, 9bc79c4
Timestamp UTC: 2026-08-22T22:30Z
Focused red failures observed per task: 모듈 부재 Import 오류(각 Task 최초 실행에서 확인)
Focused green results:
  - TV-01~11 참조 벡터 + 결정론 재실행: 14 passed
  - 속성(Hypothesis): 슬롯 단일 소유·의존성 순서 불변
  - 성능 스모크: 60-Task < 2s (전체 벤치는 P8-T02)
  - 전체 planner 스위트: 120 passed
Adjacent: ruff/mypy strict 46파일 clean; make verify 전체 통과(종료 시점 재실행)
Notes:
  - DEC-015 파라미터형 벡터 JSON / DEC-016 성능 스모크 분리 기록
  - planner-output.schema.json risk_level 대문자 정합화(구현 계약 우선, 하향 아님)
Residual risk: RISK_REGISTER 유지. 20k 속성 시나리오 실행은 P8-T02에서 산출

```

### PLAN-002 회귀 적발 기록 (Phase 2 종료 직후)

```text
Date: 2026-08-22T22:45Z
Event: make verify 실행 중 Hypothesis 속성 테스트(test_dependency_order_is_never_violated)가
       의존성 체인에서 후행 작업이 선행 완료 전 배정되는 위반 사례를 생성
Root cause: serial_schedule에 Blocks Start 시작 게이트 미구현 (준비 집합 루프 누락)
Fix: start_gates 매개변수로 게이트 전달 → 완전 배정된 선행작업만 게이트 해제,
     게이트 미해제 잔여 작업은 unallocated 처리
Proof: 수정 전 실패 재현(29 failed) → 수정 후 packages/planner/tests 120 passed,
       make verify exit=0 (커밋 2feaba9)
Rule IDs: PLAN-002, REQ-PLN-010
```
