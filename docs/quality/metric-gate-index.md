# Metric and Release Gate Index

This index is generated from the approved Evaluation and Pilot Plan. Thresholds are immutable after results are observed. The implementation must produce the named machine-readable evidence or an ADR-approved equivalent path recorded here.

| Metric ID | Metric | Approved threshold | Implementing Tasks | Canonical evidence |
|---|---|---|---|---|
| AI-001 | First-pass 구조화 스키마 성공률 | 98.5% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-002 | 1회 복구 후 최종 스키마 성공률 | 99.5% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-003 | 자동 등록된 마감·일정의 원본 출처 연결률 | 100% | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-004 | 원본에 없는 마감 시각 생성률 | 0% | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-005 | 문서 지시문을 사용자 명령으로 해석 | 0건 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-010 | 날짜·시각 Precision | 99.0% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-011 | 날짜·시각 Recall | 95.0% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-012 | 자동 등록 대상 Precision | 99.5% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-013 | 고위험 모호성 확인 전환 Recall | 98.0% 이상 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-014 | 출처 충돌 자동 선택 | 0건 | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| AI-015 | 날짜만 있는 마감의 `time_known=false` 처리 | 100% | P4-T04–P4-T08, P8-T03 | reports/stage-b/ai-structure-and-golden.json |
| EXT-001 | 정상 권한 상태의 Calendar 쓰기 성공률 | 99.5% 이상 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-002 | 동일 Idempotency Key 중복 이벤트 | 0건 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-003 | 내부 성공·외부 실패 상태 혼동 | 0건 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-004 | 권한 만료 감지 정확도 | 100% | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-005 | 외부 삭제·이동 감지 후 잘못된 강제 복원 | 0건 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-006 | Outbox 유실 | 0건 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| EXT-007 | 재시도 후 외부 ID 연결 누락 | 0건 | P5-T01–P5-T08, P8-T04 | reports/stage-c/external-execution.json |
| OPS-001 | 비LLM API P95 | 500ms 이하 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-002 | 채팅 첫 스트림 응답 P95 | 2초 이하 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-003 | 짧은 자연어 입력 최종 처리 P95 | 8초 이하 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-004 | 문서 처리 성공률 | 98% 이상 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-005 | 계획 생성 실패율 | 0.5% 이하 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-006 | 알림 발송 성공률 | 99% 이상 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-007 | 동일 문서 재분석 캐시 적중률 | 90% 이상 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OPS-008 | 실패·재시도 비용 비중 | 총 LLM 비용의 5% 이하 | P8-T01, P8-T04, P8-T06, P8-T10 | reports/stage-c/operations.json |
| OUT-001 | 계획 정리·수정 시간 중앙값 감소 | Baseline 대비 30% 이상 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-002 | 오늘 할 일 결정 부담도 | 7점 척도 1.0점 이상 개선 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-003 | 주간 수동 계획 수정률 | 20% 이하 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-004 | 자동 변경 되돌리기율 | 5% 이하 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-005 | Week 4 활성 잔존율 | 60% 이상 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-006 | 자동화 신뢰 중앙값 | 5.5/7 이상 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-007 | 주간 가치 평가 중앙값 | 5.5/7 이상 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-008 | 과부하 Proposal 유효 처리율 | 60% 이상 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-009 | 일반 날 알림 중앙값 | 4회 이하 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| OUT-010 | 알림 완전 비활성화 사용자 | 15% 이하 | P8-T09, P8-T10 | reports/pilot/outcome-metrics.json |
| PLAN-001 | 한 Pass 안의 시간 슬롯 중복 배정 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-002 | 의존성 순서 위반 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-003 | Fixed Busy와 Task 중첩 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-004 | 확정 계획이 일일 계획 가능 용량 초과 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-005 | 필수 참조 테스트 벡터 통과율 | 100% | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-006 | 동일 입력 반복 실행 결과 일치율 | 100% | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-007 | 의존성 사이클을 정상 계획으로 배정 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-008 | 날짜만 있는 마감에 임의 시각을 사실 저장 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PLAN-009 | 실패한 재계획이 정상 계획을 덮어씀 | 0건 | P2-T03–P2-T10, P8-T02 | reports/stage-a/planner-hard-gates.json |
| PQ-001 | 규범 테스트 벡터 통과 | 100% | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-002 | 속성 기반 불변 조건 통과 | 100% | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-003 | 전역 슬롯 중복 | 0건 | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-004 | Base 가능성 오판 | 0건 | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-005 | 날짜·시간 동일 입력의 결과 불일치 | 0건 | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-006 | 동결 구간 무단 변경 | 0건 | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| PQ-007 | 사용자 Pin 무단 변경 | 0건 | P2-T10, P8-T02 | reports/stage-a/planner-quality.json |
| SAFE-001 | 승인 없는 Hard Deadline 변경 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| SAFE-002 | 승인 없는 Fixed Event 변경·삭제 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| SAFE-003 | 사용자 소유권 우회 접근 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| SAFE-004 | 실패한 외부 행동을 성공으로 표시 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| SAFE-005 | 동일 외부 행동 중복 실행 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| SAFE-006 | 문서 지시문이 도구 행동으로 실행 | 0건 | P1-T06, P3-T04, P3-T05, P5-T05, P8-T05, P8-T10 | reports/stage-a/security-hard-gates.json |
| UX-001 | 새 자연어 Task 입력 | 10초 이하 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |
| UX-002 | 아침 가용 시간·컨디션 확인 | 30초 이하 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |
| UX-003 | 오늘 계획 이해 후 첫 행동 | 60초 이하 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |
| UX-004 | Task 시작 | 1회 선택 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |
| UX-005 | 완료·부분 완료·막힘 | 2회 선택 이하 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |
| UX-006 | 주간 리뷰 승인 | 5분 이하 | P7-T02–P7-T10, P8-T09 | reports/ux/interaction-and-accessibility.json |

## Integrity

- Metric IDs indexed: **64**
- A Hard Gate violation forces release **Fail** regardless of aggregate scores.
- `P8-T10` recomputes and hashes all evidence before producing the final verdict.
