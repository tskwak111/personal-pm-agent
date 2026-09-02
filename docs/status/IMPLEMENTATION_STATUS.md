# 구현 상태

- **Local Production Readiness:** PASS
- **Release:** BLOCKED_EXTERNAL
- **현재 Phase:** Release preparation — BLOCKED_EXTERNAL
- **현재 Task:** external release evidence collection
- **마지막 로컬 검증:** `make verify` PASS; Python unit 295, API client 2, Web unit 41, PostgreSQL integration 249, standalone E2E/axe 16, Stage A 20,000/15 gates PASS — revision `02674bc`, 2026-08-31 실측
- **기준 브랜치:** `main` (`a34935f`)

## Phase 현황

| Phase | 상태 | 완료 조건 |
|---|---|---|
| 0. Foundation | Implemented — local evidence recorded | 공통 명령·툴체인·로컬 서비스 계약 |
| 1. Domain Core | Implemented — local evidence recorded | 상태·권한·의존성 도메인 계약 |
| 2. Planner Engine | Implemented — local evidence recorded | 참조 벡터와 Planner 불변 조건 |
| 3. Persistence & API | Implemented — local evidence recorded | 소유권·버전·트랜잭션·OpenAPI |
| 4. Intake & LLM | Implemented — local evidence recorded | 구조화·출처·불확실성 계약 |
| 5. Calendar & Execution | Local fake/fault gates only | Outbox·멱등성·거짓 성공 방지; live provider는 외부 차단 |
| 6. Agent & Briefing | Implemented — local evidence recorded | 권한·승인·알림·operation stream 계약 |
| 7. Web/PWA | Implemented — browser evidence recorded | 실 API 기반 16 Playwright·axe·production build |
| 8. Evaluation & Release | Local tooling implemented / BLOCKED_EXTERNAL | Stage A 로컬 PASS; private corpus·live provider·pilot·운영 배포는 미검증 |

## 현재 차단 사항

| 차단 증거 | 필요한 완료 증거 |
|---|---|
| Stage B private corpus | 고정 private holdout manifest와 임계값 통과 report |
| Stage C live provider | 실제 Google 자격증명 기반 fault/reconciliation report |
| Registry/cluster | push된 application image digest와 rollout/rollback·probe 관측 |
| Managed backup | 운영 RPO/RTO를 포함한 restore drill |
| Advisory/security | 관리형 anti-malware/signature 검증, 의존성 advisory·침투 검토 결과와 remediation |
| Stage D pilot | 동의된 baseline 1주 + agent 4주 outcome report |
| Production observability | Prometheus scrape와 alert delivery 관측 |

## 최근 완료 기록

| 날짜 | Task | 검증 | 커밋 |
|---|---|---|---|
| 2026-08-26 | P8-T01~T10 평가·보안·배포 게이트 | make verify EXIT=0 (235 unit), Stage A 리포트 PASS, 배포 계약 OK | (Phase 8 커밋들) |
| 2026-08-26 | P7-T02~T10 Web/PWA 화면 전체 | make verify EXIT=0, web 23 passed, build OK | (Phase 7 커밋들) |
| 2026-08-26 | P7-T01 반응형 앱 셸·디자인 토큰 | web 3 passed, lint/typecheck OK | 07e5a8e |
| 2026-08-26 | P6-T01~T08 Agent & Briefing 전체 | make verify EXIT=0 (194 unit), api 통합 77 passed | (Phase 6 커밋들) |
| 2026-08-26 | P5-T01~T08 Calendar & Execution 전체 | make verify EXIT=0 (180 unit), api 통합 56 passed, Stage C fault 리포트 all_passed=True | (Phase 5 커밋들) |
| 2026-08-26 | P4-T01~T08 Intake·파일·LLM 전체 | make verify EXIT=0 (165 unit), api 통합 39 passed, golden eval AI-001/002 리포트 산출 | (Phase 4 커밋들) |
| 2026-08-24 | P3-T09 OpenAPI+TS 클라이언트 | test_openapi 1 passed, export_openapi + pnpm generate + typecheck 통과, 7 paths | (본 커밋) |
| 2026-08-24 | P3-T07 Immutable Plan Snapshots | valid append current / invalid preserve last-valid 2 passed, R-012 해소(registry+세션 누수) | (본 커밋) |
| 2026-08-23 | P3-T08 Transactional Outbox+실행 레코드 | 크래시 무기록·멱등 unique·검증 불변식 4 passed | fe289e7 |
| 2026-08-23 | P3-T06 Planning Core 커맨드 API | DONE 잔여시간 422/Hard Deadline→202 RECONFIRM Proposal | ec9d750 |
| 2026-08-23 | P3-T05 낙관적 동시성+멱등키 | PATCH v1→200/v2, 재시도 409, 감사 이벤트 동시 기록 | 43434a1 |
| 2026-08-23 | P3-T04 신원 세션·소유권 가드 | 401/404/스코핑 3 passed, ORM relationship 삽입 순서 수정 | (본 커밋) |
| 2026-08-23 | P3-T03 리포지토리+Unit of Work | 도메인+감사 원자적 커밋/예외 시 전부 롤백 검증 | 1f0313c |
| 2026-08-23 | P3-T02 Planning Core 스키마+마이그레이션 | FK/CHECK/partial-unique 제약 테스트, upgrade/downgrade 사이클 | 45f3bdc |
| 2026-08-23 | P3-T01 비동기 DB 세션·Alembic 기반 | 롤백 원자성 테스트, upgrade head 실측 | 3af5f58 |
| 2026-08-23 | P2-T10 plan() 오케스트레이터+TV-01~11+속성+성능 스모크 | 120 passed, ruff/mypy clean | 9bc79c4 |
| 2026-08-23 | P2-T09 오늘 계획·최소변경 재계획·Proposal | 사전식 목적 순서·동결/Pin 보호 검증 | d1d518b |
| 2026-08-23 | P2-T08 전역 배정 기반 위험 분류 | Definitive/Unknown/Capacity/High/Medium/Low 순서 테스트 | 57abc77 |
| 2026-08-23 | P2-T07 Provisional/Base/Safety Pass+합성 버퍼 | 독립 슬롯 장부·P0 승격 1회·버퍼 실슬롯 점유 | 9eb4f10 |
| 2026-08-23 | P2-T06 직렬 일정 생성(분할/비분할) | TV-01·TV-08 케이스 GREEN, 슬롯 단일 소유 검증 | d685f5a |
| 2026-08-23 | P2-T05 우선순위 등급·동률 튜플 | focused RED→GREEN, LLM 점수 배제 검증 | 166ef81/d3853b0 |
| 2026-08-23 | P2-T04 의존성 타이밍·사이클·핸드오프 역산 | latest_safe_handoff/must_start_by/unlock 검증 | 6605cf4 |
| 2026-08-23 | P2-T03 고유 슬롯 생성·용량 예약 | FIXED/FOCUS/BUFFER 단일 소유권, 일일 계획가능 비율 | 0c3d312 |
| 2026-08-23 | P2-T02 날짜 해석·안전 추정 산출 | date-only 자정 경계, 샘플 강도 혼합 | 13cef0f |
| 2026-08-23 | P2-T01 입력 검증·정규화 | INVALID_INPUT Rule ID, 순서 무관 해시 | 1ca6e0e |
| 2026-08-23 | P1-T07 Planner 입출력 계약 동결 | focused RED→GREEN, 순서 무관 직렬화 48 passed | afb90f0 |
| 2026-08-23 | P1-T06 승인·권한·감사 정책 | focused RED→GREEN, 43 passed | cabd3a0 |
| 2026-08-23 | P1-T05 가용·캘린더·외부 의존성 스냅샷 | focused RED→GREEN, 34 passed | 3b47b49 |
| 2026-08-23 | P1-T04 의존성 그래프·사이클 계약 | SCC 안정 경로 검증 포함 28 passed | ac39fa5 |
| 2026-08-23 | P1-T03 Task 스냅샷·상태 머신 | focused RED→GREEN + 전수 엣지 커버 | 01dd7b9/74c1442 |
| 2026-08-23 | P1-T02 Facts·Workstream·Milestone 스냅샷 | date-only 마감 불변식 등 13 passed | 5a19e90 |
| 2026-08-23 | P1-T01 식별자·enum·시간 원시 타입 | focused RED→GREEN 5 passed | 2cd0597 |
| 2026-08-22 | P0-T01 툴체인 핀(Phase 0 전체는 이전 표와 VERIFICATION_EVIDENCE 참조) | focused RED→GREEN | 91fe556 |

## 다음 행동

1. 전체 브랜치 self-review의 Critical/Important 5건은 TDD로 수정했고 scoped re-review에서 잔여 0건이다.
2. 최종 완료 매트릭스를 재실행한 뒤 `main`에 fast-forward 병합했다.
3. 외부 증거 표가 남아 있으므로 release는 계속 차단한다.
