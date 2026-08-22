# Personal PM Agent — Release Audit Prompt

현재 release candidate가 Personal PM Agent Evaluation Spec의 출시 조건을 충족하는지 독립적으로 감사하라. 기능이 구현됐다는 주장이나 이전 보고서를 신뢰하지 말고 원본 결과와 fresh command로 확인한다.

## 감사 입력

- release commit SHA
- Planner version
- API/Web/Worker version
- model과 prompt version
- dataset version과 split hash
- infrastructure version
- migration head
- Stage A/B/C report artifacts
- incident log

입력이 없으면 저장소와 CI artifact에서 찾고, 찾을 수 없는 항목은 누락으로 기록한다.

## 필수 감사

1. clean checkout과 lockfile 재현성
2. 전체 lint, typecheck, unit, integration, E2E와 build
3. Planner TV-01~TV-11와 속성 기반 Hard Gate
4. ownership, approval, outbox, idempotency와 거짓 성공 Gate
5. Stage B golden/private split 오염 여부와 metric 재계산
6. Stage C fault injection과 외부 ID reconciliation
7. migration blank/upgrade, backup/restore와 deletion verification
8. security scan, secret scan, dependency audit와 log redaction
9. Metric threshold 변경 이력과 사후 하향 여부
10. S0~S3 Incident와 미해결 위험

## 금지

- 실패 사례를 분모에서 제외하지 않는다.
- retry 성공을 first-pass로 계산하지 않는다.
- 평균만 보고 P90·분포를 생략하지 않는다.
- 현재 release를 통과시키기 위해 threshold를 변경하지 않는다.
- 실행하지 못한 Gate를 통과로 추정하지 않는다.
- S0/S1를 다른 좋은 지표로 상쇄하지 않는다.

## 판정

Evaluation Spec의 다음 규칙만 사용한다.

- `Pass`
- `Conditional Pass`
- `Fail`

Conditional Pass는 안전·권한·Planner Hard Gate와 필수 Outcome Gate가 모두 통과한 경우에만 가능하다.

## 보고서 형식

```text
1. 감사 대상 버전
2. 실행 환경과 명령
3. Artifact 무결성
4. Stage A 결과
5. Stage B 결과
6. Stage C 결과
7. Security·Migration·Backup 결과
8. Incident와 미해결 위험
9. Gate별 Pass/Fail 표
10. 판정과 정확한 근거
11. 출시 차단 항목
12. 다음 재평가 조건
```

각 주장에 command output, report path, metric numerator/denominator 또는 코드 위치 중 하나 이상의 증거를 붙여라.
