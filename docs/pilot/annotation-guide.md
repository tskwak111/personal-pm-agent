# 전문가 시나리오 어노테이션 가이드 (요약)

- `expected_kind`: HARD_DEADLINE / FIXED_EVENT / REFERENCE_NOTE / AMBIGUOUS
- 시각이 문장에 명시된 경우에만 `expected_time_known: true`
- P0 = 오늘~내일 마감, P1 = 이번 주, P2 = 그 외, 위험 없으면 null
- 두 명 독립 라벨 → 불일치는 제3자 재검토
