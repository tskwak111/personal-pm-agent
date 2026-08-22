# 결정 기록

| ID | 날짜 | 결정 | 근거 | 상태 |
|---|---|---|---|---|
| DEC-001 | 2026-08-23 | Planning Core를 공식 상태의 단일 기준으로 사용 | 채팅·LLM 메모리의 비결정성과 상태 손실 방지 | Accepted |
| DEC-002 | 2026-08-23 | Planner를 순수 Python 패키지로 분리 | 결정론, 속성 기반 테스트, 독립 성능 측정 | Accepted |
| DEC-003 | 2026-08-23 | Next.js Web/PWA + FastAPI Modular Monolith | UX와 Python AI/Planner 생태계의 책임 분리 | Accepted |
| DEC-004 | 2026-08-23 | PostgreSQL + Redis + S3-compatible Object Storage | 트랜잭션, 큐, 원본 보존 요구 | Accepted |
| DEC-005 | 2026-08-23 | Google Calendar만 초기 외부 캘린더로 지원 | 핵심 가치 검증과 동기화 복잡성 제한 | Accepted |
| DEC-006 | 2026-08-23 | Base Pass와 Safety Pass를 독립 전역 배정 | 공유 가용 시간 중복 계산 방지 | Accepted |
| DEC-007 | 2026-08-23 | 재계획은 사전식 목적 순서를 사용 | 안전과 위험 감소를 계획 안정성보다 우선 | Accepted |
| DEC-008 | 2026-08-23 | 외부 실행은 Transactional Outbox와 Idempotency를 사용 | DB와 외부 API의 원자성 부재 대응 | Accepted |
| DEC-009 | 2026-08-23 | 평가 합격선을 코드보다 먼저 고정 | 결과에 맞춘 기준 하향 방지 | Accepted |
| DEC-010 | 2026-08-23 | 배포 매니페스트 검증 범위를 패키지 문서 세트로 한정하고 VCS·런타임 디렉터리를 제외 | `verify_package.py`의 전체 트리 커버리지 검사는 Git 초기화와 동시에 실패한다(`.git/**` 포함). AGENTS.md §1/§6은 저장소 발전 후에도 검증 통과를, §8은 상태 문서 갱신을 요구하므로 바이트 동결 해석은 자기모순. 규범 스펙 3종은 `SOURCE_SPEC_HASHES.sha256`로 계속 동결하며 구조·추적·지표 검사는 유지 | Accepted |
| DEC-011 | 2026-08-23 | 루트 패치 핀: Python 3.13.15, Node 24.19.0, pnpm 10.34.5 | toolchain-baseline.md의 patch-selection gate: 공식 배포판 확인, 설치 환경에서 실측(`uv python list`, `node --version`, `pnpm --version`), `.python-version`/`.node-version`/`packageManager`에 고정 | Accepted |
| DEC-012 | 2026-08-23 | 로컬 compose는 메이저 태그(postgres:18, redis:8, minio/minio) 사용, 불변 다이제스트 핀은 레지스트리 접근 가능 시점(P8 배포 경화 전)으로 연기 | toolchain-baseline은 "검증되지 않은 패치를 current/secure로 서술 금지"를 요구. 실행 환경에서 레지스트리 조회가 타임아웃으로 실패해 다이제스트 실측 불가. RISK-001로 추적 | Accepted |
| DEC-013 | 2026-08-23 | compose 호스트 포트를 환경변수 오버라이드로 제공하고 PG18 이미지의 `/var/lib/postgresql` 볼륨 레이아웃을 채택 | 개발 환경의 기존 로컬 PostgreSQL(5432 사용 중)과 충돌 없이 검증하기 위함. PG18 공식 이미지는 메이저별 하위 디렉터리 레이아웃을 요구하며 실측(pg_isready healthy, PostgreSQL 18.6 응답)으로 확인 | Accepted |

새 결정은 `DEC-014`부터 추가한다. 장기적·구조적 결정은 `docs/architecture/adr/`에 별도 ADR을 생성하고 이 표에서 연결한다.
