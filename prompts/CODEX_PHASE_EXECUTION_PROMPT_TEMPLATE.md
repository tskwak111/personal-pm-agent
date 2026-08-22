# Personal PM Agent — Phase Execution Prompt Template

아래 대괄호 값을 현재 작업에 맞게 교체한 뒤 사용한다.

```text
Personal PM Agent 저장소에서 [PHASE PLAN PATH]의 [TASK NUMBER AND TITLE]만 구현하라.

먼저 AGENTS.md, 세 규범 명세, 현재 Phase 계획, IMPLEMENTATION_STATUS와 Traceability를 읽어라. 기존 구현과 git 상태를 확인하고 전용 worktree/branch에서 작업하라.

Task의 Files와 Interfaces 계약을 그대로 지키고, downstream 공개 이름을 임의 변경하지 말라. 범위를 다음 Task까지 확장하지 말라.

필수 실행 순서:
1. 실패하는 최소 테스트 작성
2. 정확한 RED 결과 확인
3. 최소 구현
4. focused test 통과
5. 인접 unit/integration 회귀
6. lint와 typecheck
7. 필요한 build/E2E
8. diff review
9. Phase checkbox, IMPLEMENTATION_STATUS와 Traceability 갱신
10. 원자적 commit
11. fresh completion verification

Planner·권한·외부 실행·사용자 소유권 Hard Gate를 우회하지 말라. 테스트를 skip하거나 기대값을 구현에 맞춰 낮추지 말라. 불가피한 규범 충돌만 구체적인 재현 사례와 함께 질문하라.

완료 보고에는 변경 파일, Requirement ID, RED/GREEN 증거, 전체 검증 결과, commit SHA, 남은 위험과 다음 Task를 포함하라.
```
