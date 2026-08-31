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
| DEC-014 | 2026-08-23 | Task 상태 머신에 `Ready→Waiting`, `Ready→Blocked` 엣지를 포함하고, Waiting 이탈 시 사유를 해소로 표기하며 CANCELLED 진입 시 잔여량을 0으로 정리 | 도메인 상태 문서 §1 전이표에 없는 두 엣지는 Phase 1 계획(P1-T03)의 허용 테이블에 명시됨. 설계 §14.4가 Blocked/Waiting을 시작 여부와 무관한 원인 상태로 정의하므로 Ready 단계의 외부 대기·장애 기록이 제품 행동과 일치. 권한·승인에 영향 없음. 전수 엣지 테스트로 고정 | Accepted |

| DEC-015 | 2026-08-23 | 참조 벡터를 파라미터형 JSON(tv-01~11)로 관리하고 Stage A 속성 시나리오 수는 CI 25예제/평가 시 20,000 확장 구조로 운영 | 벡터의 본질은 입력 파라미터와 기대 불변식의 버전 관리이며, 전체 PlannerInput 스냅샷 인라인은 중복 대량 파일을 낳음. PLAN-005/006·PQ 게이트는 동일 코드 경로로 확장 실행됨 | Accepted |
| DEC-016 | 2026-08-23 | 500-Task 성능 벤치는 P8-T02 Stage A 리포트에서 정식 산출하고, 커밋마다는 60-Task 2초 스모크로 회귀 트립워브 유지 | 전체 벤치는 단위 테스트 예산을 초과하며 평가 계획상 Stage A 산출물임. 스모크는 회귀 조기 감지 목적 | Accepted |
| DEC-017 | 2026-08-31 | 로컬 production-readiness와 실제 release 판정을 분리한다 | 저장소 내 결정론적 검증은 로컬 품질을 증명하지만 private corpus, live provider, 운영 인프라, advisory와 실제 사용자를 대신할 수 없다 | Accepted |
| DEC-018 | 2026-08-31 | API 인증은 bearer-only로 고정하고 인증 cookie를 받지 않는다 | 브라우저가 자동 첨부하는 인증 cookie가 없으므로 CSRF token을 별도 상태로 추가하지 않고 cookie-only 요청을 401로 거부한다 | Accepted |
| DEC-019 | 2026-08-31 | Kubernetes application image는 배포 시 registry digest를 주입하고 renderer가 형식을 검증한다 | 저장소가 알 수 없는 미래 registry digest를 가짜로 고정하지 않으면서 mutable tag 배포를 막는다 | Accepted |
| DEC-020 | 2026-08-31 | 현재 runtime metric registry는 프로세스 내부 bounded-label 구현으로 제한한다 | 추가 collector 의존성 없이 alert/dashboard 계약을 검증한다. 다중 replica 집계는 production scrape 검증 시 외부 collector로 승격한다 | Accepted |

새 결정은 `DEC-021`부터 추가한다. 장기적·구조적 결정은 `docs/architecture/adr/`에 별도 ADR을 생성하고 이 표에서 연결한다.
