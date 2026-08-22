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

새 결정은 `DEC-010`부터 추가한다. 장기적·구조적 결정은 `docs/architecture/adr/`에 별도 ADR을 생성하고 이 표에서 연결한다.
