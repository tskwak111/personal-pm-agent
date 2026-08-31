# 위험 등록부

| ID | 위험 | 가능성 | 영향 | 현재 완화책 | 상태 |
|---|---|---:|---:|---|---|
| R-001 | LLM이 마감·일정을 잘못 자동 등록 | Medium | Critical | 구현됨: evidence.py(자신감 배제), registration_policy(충돌/시간미상/고피해 항상 확인), intake 어댑터 source span 바인딩, golden eval AI-001/002 | Mitigated (P8 평가에서 최종 확인) |
| R-002 | Planner가 같은 가용 시간을 중복 사용 | Low after tests | Critical | 고유 슬롯, Base/Safety 독립 Pass, 보호된 이전 배정도 양쪽 Ledger에 예약, 속성·참조 벡터·전체 Planner 테스트 | Mitigated |
| R-003 | 의존성 사이클로 계획이 불가능 | Medium | High | SCC 탐지, 자동 수정 금지, Blocked 표시 | Open |
| R-004 | 계획이 자주 바뀌어 사용자 신뢰 하락 | Medium | High | Freeze Window·핀 배정을 승인 전 원위치로 보존하고 회귀 테스트로 고정; 실제 신뢰 영향은 파일럿 필요 | Open |
| R-005 | Google Calendar 중복 생성 또는 거짓 성공 | Medium | Critical | 저장소 검증: 실행기 부재/검증 실패는 FAILED, 멱등 실행기, 타임아웃 PENDING, Stage C fault 시나리오. 실제 Google 자격증명 기반 종단 증거는 없음 | Open (live-provider proof required) |
| R-006 | OAuth 토큰 또는 개인 문서 노출 | Low | Catastrophic | 구현됨: AES-GCM 볼트, 로그 REDACTED 필터(테스트), 워크스페이스 해싱, 텔레메트리 민감필드 거부, 백업 암호화 | Mitigated |
| R-007 | 문서 프롬프트 인젝션이 행동으로 이어짐 | Medium | Catastrophic | content 격리, tool-less extraction, approval | Open |
| R-008 | 전체 기능 규모로 일정 지연 | High | Medium | Phase gate, 독립 Task, 우선 핵심 경로 구현 | Accepted |
| R-009 | 실제 사용자가 체크인을 귀찮아함 | Medium | High | 구현됨: 원액션 작업 시작, 2탭 이내 완료/부분/막힘, UX-001..006 계측으로 파일럿 측정 준비 | Mitigated (P8 파일럿에서 측정) |
| R-010 | 예상 시간 보정이 적은 표본에서 왜곡 | Medium | Medium | 표본별 반영 강도, factor clamp, reset | Open |
| R-012 | 전체 verify 수집 시 간헐 라이브락(개별 스위트는 green). asyncpg 풀 × 루프 리셋 × 세션스코프 마이그레이션 상호작용 추정 | High | High | 2026-08-24 해소: 원인=①workspaces.models에서 UserSessionModel 레지스트리 미로드로 매퍼 초기화 실패 ②PlanningService 세션이 테스트 종료 시 close되지 않아 engine.dispose 블록 ③migrated_database downgrade가 풀 대기. 수정: workspaces.models에 identity import, clean_tables에 NullPool+전후 truncate, session close, 마이그레이션 downgrade 제거. 재실행 25 passed/2.45s, make verify 통과로 Close | Closed |
| R-011 | 로컬 컨테이너가 메이저 태그로 참조되어 재현성 저하 | Medium | Low | 레지스트리 접근 가능 시 불변 다이제스트로 고정(DEC-012), P8 배포 경화 전 필수 | Open |

위험이 현실화되면 Incident ID와 관련 테스트를 연결한다.
