# Personal PM Agent — Codex Resume Prompt

이 저장소의 개발을 이전 상태에서 정확히 이어서 진행하라. 완료된 작업을 처음부터 다시 만들거나 문서를 재요약하지 말라.

## 재개 절차

1. 다음을 실행한다.

```bash
git status --short --branch
python3 scripts/verify_package.py
```

2. 다음을 읽는다.

```text
AGENTS.md
docs/status/IMPLEMENTATION_STATUS.md
docs/status/HANDOFF_CHECKLIST.md
docs/status/DECISION_LOG.md
docs/status/RISK_REGISTER.md
docs/plans/00-master-implementation-roadmap.md
현재 Phase 계획
git log --oneline --decorate -20
```

3. 작업 트리에 미커밋 변경이 있으면 먼저 출처와 의도를 파악한다. 사용자 변경을 덮어쓰지 않는다.
4. 현재 Phase의 첫 미완료 Task와 마지막 완료 커밋을 비교한다.
5. 마지막 완료 보고의 검증 명령을 다시 실행해 기준선을 확인한다.
6. 부분 구현이 있으면 테스트와 diff로 실제 상태를 판별한다. 체크박스나 이전 에이전트의 성공 주장만 신뢰하지 않는다.
7. 첫 미완료 Task의 가장 작은 실패 테스트부터 이어간다.

## 필수 규칙

- 제품, Planner와 평가 규범을 다시 완화하지 않는다.
- 동일한 인터페이스를 새 이름으로 중복 구현하지 않는다.
- 이미 통과한 Task를 이유 없이 리팩터링하지 않는다.
- 실패한 기준선이 있으면 기능 구현보다 원인 파악을 먼저 한다.
- 완료 주장 전 fresh verification을 실행한다.
- Task 완료 시 Status, Traceability, Decision/Risk와 Phase 체크박스를 갱신한다.

## 첫 보고 형식

```text
재개 상태
- Branch/worktree:
- Last verified commit:
- Current Phase / Task:
- Working tree changes:
- Baseline result:

이어갈 작업
- 첫 실패 테스트:
- 대상 파일:
- 완료 검증:
```

상태 보고 후 바로 작업을 계속하라.
