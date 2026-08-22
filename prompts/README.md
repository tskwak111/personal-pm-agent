# Codex Prompt 사용 안내

| 파일 | 사용 시점 |
|---|---|
| `CODEX_MASTER_META_PROMPT.md` | 문서 패키지만 있는 새 저장소에서 전체 개발을 처음 시작할 때 |
| `CODEX_PHASE_PROMPTS.md` | 이전 Phase가 검증된 상태에서 특정 Phase를 재개할 때 |
| `CODEX_RESUME_PROMPT.md` | 세션이 끊겼거나 미커밋 변경이 있는 저장소의 실제 상태를 먼저 복원할 때 |
| `CODEX_PHASE_EXECUTION_PROMPT_TEMPLATE.md` | 한 Phase의 한 Task만 별도 worktree/agent에 위임할 때 |
| `CODE_REVIEW_PROMPT.md` | Task 또는 Phase 병합 전 spec·safety 중심 리뷰 |
| `CODEX_FINAL_AUDIT_META_PROMPT.md` | 모든 Phase 완료 주장 후 전체 구현을 독립적으로 재검증할 때 |
| `RELEASE_AUDIT_PROMPT.md` | 특정 Release Candidate의 Evaluation Gate와 판정을 공식 감사할 때 |

## 권장 흐름

```text
새 저장소
→ CODEX_MASTER_META_PROMPT
→ Task별 실행
→ CODE_REVIEW_PROMPT
→ 새 세션은 CODEX_RESUME_PROMPT 또는 CODEX_PHASE_PROMPTS
→ 전체 완료 후 CODEX_FINAL_AUDIT_META_PROMPT
→ 출시 후보마다 RELEASE_AUDIT_PROMPT
```

프롬프트보다 승인 명세, `AGENTS.md`, 상태 머신과 Phase 계획의 해당 범위 규칙이 우선한다. Master Prompt만 복사하고 개발 패키지 문서를 누락시키지 않는다.
