# 위험 등록부

| ID | 위험 | 가능성 | 영향 | 현재 완화책 | 상태 |
|---|---|---:|---:|---|---|
| R-001 | LLM이 마감·일정을 잘못 자동 등록 | Medium | Critical | 출처, evidence score, 고위험 확인, 오등록 Gate | Open |
| R-002 | Planner가 같은 가용 시간을 중복 사용 | Low after tests | Critical | 고유 슬롯, Base/Safety 독립 Pass, 속성 테스트 | Open |
| R-003 | 의존성 사이클로 계획이 불가능 | Medium | High | SCC 탐지, 자동 수정 금지, Blocked 표시 | Open |
| R-004 | 계획이 자주 바뀌어 사용자 신뢰 하락 | Medium | High | Freeze Window, 변경 비용, change ratio Gate | Open |
| R-005 | Google Calendar 중복 생성 또는 거짓 성공 | Medium | Critical | Outbox, idempotency, 외부 ID, fault injection | Open |
| R-006 | OAuth 토큰 또는 개인 문서 노출 | Low | Catastrophic | encryption, 최소 권한, 로그 제거, incident gate | Open |
| R-007 | 문서 프롬프트 인젝션이 행동으로 이어짐 | Medium | Catastrophic | content 격리, tool-less extraction, approval | Open |
| R-008 | 전체 기능 규모로 일정 지연 | High | Medium | Phase gate, 독립 Task, 우선 핵심 경로 구현 | Accepted |
| R-009 | 실제 사용자가 체크인을 귀찮아함 | Medium | High | 30초 UX Gate, 묶음 알림, 파일럿 측정 | Open |
| R-010 | 예상 시간 보정이 적은 표본에서 왜곡 | Medium | Medium | 표본별 반영 강도, factor clamp, reset | Open |
| R-011 | 로컬 컨테이너가 메이저 태그로 참조되어 재현성 저하 | Medium | Low | 레지스트리 접근 가능 시 불변 다이제스트로 고정(DEC-012), P8 배포 경화 전 필수 | Open |

위험이 현실화되면 Incident ID와 관련 테스트를 연결한다.
