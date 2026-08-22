# 저장소와 모듈 경계 계약

## 1. 목표 저장소 구조

```text
personal-pm-agent/
├─ AGENTS.md
├─ README.md
├─ Makefile
├─ package.json
├─ pnpm-workspace.yaml
├─ pnpm-lock.yaml
├─ pyproject.toml
├─ uv.lock
├─ .python-version
├─ .node-version
├─ .env.example
├─ compose.yaml
├─ apps/
│  ├─ api/
│  │  ├─ pyproject.toml
│  │  ├─ src/personal_pm_api/
│  │  │  ├─ main.py
│  │  │  ├─ settings.py
│  │  │  ├─ identity/
│  │  │  ├─ inbox/
│  │  │  ├─ workspaces/
│  │  │  ├─ planning/
│  │  │  ├─ approvals/
│  │  │  ├─ calendar/
│  │  │  ├─ execution/
│  │  │  ├─ notifications/
│  │  │  ├─ analytics/
│  │  │  ├─ agent/
│  │  │  ├─ audit/
│  │  │  └─ shared/
│  │  └─ tests/
│  ├─ worker/
│  │  ├─ pyproject.toml
│  │  ├─ src/personal_pm_worker/
│  │  └─ tests/
│  └─ web/
│     ├─ package.json
│     ├─ src/app/
│     ├─ src/features/
│     ├─ src/components/
│     ├─ src/lib/
│     ├─ src/test/
│     └─ e2e/
├─ packages/
│  ├─ planner/
│  │  ├─ pyproject.toml
│  │  ├─ src/personal_pm_planner/
│  │  │  ├─ domain/
│  │  │  ├─ normalization/
│  │  │  ├─ graph/
│  │  │  ├─ availability/
│  │  │  ├─ scheduling/
│  │  │  ├─ risk/
│  │  │  ├─ replanning/
│  │  │  ├─ proposals/
│  │  │  └─ contracts/
│  │  └─ tests/
│  ├─ api-client/
│  ├─ ui/
│  └─ config/
├─ evals/
│  ├─ golden/
│  ├─ planner-vectors/
│  ├─ expert-scenarios/
│  ├─ fault-injection/
│  └─ reports/
├─ infra/
│  ├─ docker/
│  ├─ deployment/
│  ├─ monitoring/
│  └─ backup/
├─ scripts/
└─ docs/
```

## 2. 의존 방향

```text
Web → Generated API Client → API Application Services
API Application Services → Domain Ports + Planner Package
Infrastructure Adapters → Domain/Application Ports
Worker → Application Services + Infrastructure Adapters
Planner Package → Python standard library only
```

금지 방향:

```text
Planner → FastAPI / SQLAlchemy / Redis / LLM SDK / Google SDK
Domain → API Router / React / ORM Model
LLM Adapter → Repository 직접 수정
Web → Database
Worker → 다른 모듈 테이블의 임의 SQL
```

## 3. Python 경계

- `packages/planner`는 순수 Python 패키지다.
- `apps/api`는 HTTP, application orchestration, persistence adapter와 auth를 담당한다.
- `apps/worker`는 outbox, 문서 처리, LLM 호출, 동기화와 알림 작업을 실행한다.
- API와 Worker가 공유하는 application 코드는 `apps/api/src/personal_pm_api`의 명시적 service 또는 별도 package로 승격한다.
- ORM 객체를 Planner 입력으로 직접 넘기지 않고 immutable snapshot으로 변환한다.

## 4. TypeScript 경계

- App Router를 사용한다.
- 서버 상태는 TanStack Query 또는 Server Component fetch 계약으로 관리한다.
- OpenAPI 생성 타입을 단일 API 계약으로 사용한다.
- UI 상태와 서버 상태를 하나의 전역 store에 섞지 않는다.
- 기능 코드는 `src/features/<feature>`에 두고 공용 primitive만 `src/components`로 승격한다.

## 5. 데이터 경계

- PostgreSQL이 공식 상태의 단일 기준이다.
- Redis는 큐, 짧은 캐시, lock과 rate limit에만 사용한다.
- Object Storage는 원본 파일을 보관한다.
- Vector/embedding 데이터는 참고 문서 검색에만 사용한다.
- Plan Snapshot과 Audit Event는 중요한 변경 전후를 재현할 수 있어야 한다.

## 6. 외부 실행 경계

```text
Application Transaction
  ├─ 내부 상태 변경
  └─ Outbox Event 저장
        ↓
Worker
  ├─ idempotency 확인
  ├─ 외부 API 호출
  ├─ 외부 ID와 결과 저장
  └─ 실패 분류·재시도 또는 재인증 요청
```

외부 SDK 호출은 adapter 내부에만 존재한다.
