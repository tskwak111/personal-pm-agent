# 문서 권한과 충돌 해결 규칙

## 1. 범위별 기준 문서

| 범위 | 최종 기준 |
|---|---|
| 문제 정의, 목표 사용자, 제품 기능, UX, 자율성 | 제품 설계 명세 |
| Planner 입력·정규화·배정·위험·재계획 | Planner 규범 명세 |
| Metric, 합격선, 출시 판정, 중단 기준 | 평가·파일럿 명세 |
| Task·Proposal·Plan·External Execution 상태 전이와 권한 행렬 | `docs/architecture/domain-state-machines.md` |
| Requirement ID와 구현·테스트 연결 | `docs/requirements/requirements-traceability.md` |
| 사용자 관점의 완성 행동 | `docs/requirements/acceptance-scenarios.md` |
| 완료 주장과 검증 명령 | `docs/quality/definition-of-done.md`, `docs/quality/verification-command-matrix.md` |
| 저장소 경로, 구현 순서, 인터페이스 | 해당 Phase 구현계획 |
| 지속적인 에이전트 운영 규칙 | `AGENTS.md` |
| 일회성 세션 실행 지시 | Codex 메타프롬프트 |

## 2. 충돌 시 처리

1. 더 구체적인 범위의 규범 문서가 일반 설계를 보완한다.
2. Phase 계획은 규범 문서를 구현하기 위한 것이며 규범을 바꿀 수 없다.
3. 메타프롬프트는 문서 내용을 축약하거나 완화할 수 없다.
4. 두 규범 문서가 같은 범위에서 모순되면 자동으로 한쪽을 선택하지 않는다.
5. 충돌을 재현 가능한 예시로 기록하고 `docs/status/DECISION_LOG.md`에 임시 차단 상태를 남긴다.
6. 안전한 읽기·분석 작업은 계속할 수 있지만 충돌 영역의 상태 변경은 멈춘다.
7. 해결 결과는 ADR과 규범 문서 버전 변경으로 반영한다.

## 3. 변경 통제

다음 변경은 ADR과 사용자 승인 없이 허용하지 않는다.

- Planner 위험 판정 순서
- Priority Tuple 순서
- 슬롯 크기와 동결 구간 기본값
- 승인 수준 하향
- 평가 Hard Gate 또는 합격선 하향
- Planning Core의 공식 상태 범위
- LLM의 직접 실행 권한 확대
- 사용자 데이터 보관·삭제 정책 완화
