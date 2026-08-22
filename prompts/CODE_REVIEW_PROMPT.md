# Personal PM Agent — Strict Code Review Prompt

현재 branch/worktree의 변경을 승인된 Personal PM Agent 명세와 Phase 계획에 대조해 매우 엄격하게 리뷰하라. 칭찬이나 요약보다 결함 탐지와 증거를 우선한다.

## 먼저 수행

```bash
git status --short --branch
git diff --check
git diff --stat
```

변경 기준 commit과 현재 diff를 확인하고 다음을 읽는다.

- `AGENTS.md`
- 현재 Phase 계획
- 관련 제품 설계 구간
- 관련 Planner 규범 구간
- 관련 평가 Metric/Gate
- `docs/requirements/requirements-traceability.md`

## 리뷰 순서

1. **S0/S1 안전 결함**
   - 다른 Workspace 접근
   - 승인 없는 외부 행동
   - Hard Deadline·Fixed Event 무단 변경
   - 외부 실패의 거짓 성공
   - 중복 외부 실행
   - prompt injection 도구 실행

2. **Planner 규범 위반**
   - 슬롯 중복
   - 의존성·동결·Pin 위반
   - 비결정론
   - 독립적 capacity 이중 계산
   - 날짜만 있는 마감 시각 조작
   - Base/Safety/위험 순서 오류

3. **데이터 일관성**
   - ownership와 expected version 누락
   - transaction/outbox 분리
   - Plan Snapshot overwrite
   - audit 누락
   - migration data loss

4. **LLM 경계**
   - 자유 텍스트 직접 실행
   - source evidence 누락
   - model confidence 단독 자동화
   - context leakage
   - untrusted content 분리 실패

5. **테스트 품질**
   - RED 확인 없는 테스트
   - 구현 세부사항만 검증
   - 중요 branch 누락
   - mock 과사용
   - skip/xfail/flaky retry
   - Gate를 낮춘 변경

6. **코드 품질과 유지보수성**
   - 책임 혼합
   - 잘못된 계층 의존성
   - 타입 우회
   - 중복 DTO
   - 로그 민감정보
   - 성능·N+1·무제한 입력

## 직접 검증

리뷰 범위에 필요한 focused test, unit/integration, lint, typecheck와 build를 실제 실행하라. 실행하지 않은 검증은 통과로 간주하지 말라.

## 출력 형식

결함을 심각도 순으로 먼저 제시한다.

```text
[S0/S1/S2/S3] 짧은 제목
- 위치: file:line
- 위반 Requirement/Gate:
- 실제 문제:
- 재현 또는 증거:
- 사용자/시스템 영향:
- 최소 수정 방향:
- 필요한 회귀 테스트:
```

그 후 다음만 추가한다.

```text
검증 실행 결과
남은 불확실성
승인 판정: Approve / Request Changes / Block
```

실질적인 결함이 없을 때만 `Approve`를 사용한다. 스타일 선호를 규범 위반처럼 과장하지 말고, 반대로 안전·정합성 결함을 사소한 개선으로 낮추지 말라.
