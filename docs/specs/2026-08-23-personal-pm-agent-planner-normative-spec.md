# Personal PM Agent — 계획 엔진 규범 명세

- **문서 상태:** 구현 구속력이 있는 규범 명세
- **버전:** Planner Spec v1.0
- **작성일:** 2026-08-23 (Asia/Seoul)
- **상위 문서:** `2026-08-23-personal-pm-agent-design.md`
- **목적:** 같은 입력 상태에 대해 구현자와 실행 환경이 달라도 같은 계획·위험·변경안을 생성하도록 계산 규칙을 고정한다.

---

## 1. 규범 언어와 적용 범위

이 문서에서 다음 용어는 구현 의무를 뜻한다.

- **MUST:** 반드시 구현해야 한다.
- **MUST NOT:** 절대 허용하지 않는다.
- **SHOULD:** 특별한 사유가 없으면 따라야 한다.
- **MAY:** 선택적으로 구현할 수 있다.

계획 엔진은 LLM, 네트워크, 데이터베이스 SDK와 분리된 결정론적 도메인 모듈이어야 한다. LLM은 입력 구조화와 설명 문장 생성에만 사용하며, 이 문서의 계산·순서·권한 규칙을 변경할 수 없다.

핵심 목표는 다음과 같다.

1. 하나의 가용 시간 슬롯을 둘 이상의 작업에 중복 배정하지 않는다.
2. 의존성과 고정 일정을 위반하지 않는다.
3. 마감 위험을 개별 작업의 독립적인 추정이 아니라 전역 용량 배정 결과로 계산한다.
4. 동일한 입력과 동일한 Planner 버전은 바이트 수준으로 정규화했을 때 동일한 핵심 결과를 생성한다.
5. 재계획은 위험을 먼저 줄이고, 그다음 기존 계획 변경량을 최소화한다.

---

## 2. 핵심 용어

### 2.1 기준 예상 시간

`base_duration_minutes`는 현재 정보에서 가장 가능성이 높은 작업 시간의 운영 추정치다. 사용자가 보는 일반 예상 시간에 해당한다.

### 2.2 안전 예상 시간

`safety_duration_minutes`는 마감 가능성 계산과 안전 용량 배정에 사용하는 보수적 추정치다.

초기 제품은 이 값을 통계적 분위수라고 주장하지 않는다. 충분한 표본과 교정된 분포가 없는 상태에서 `P50`, `P90`이라는 이름을 사용하지 않는다.

### 2.3 기준 계획과 안전 계획

- **기준 계획(Base Pass):** `base_duration_minutes`로 생성하는 실행 가능성 계획
- **안전 계획(Safety Pass):** `safety_duration_minutes`와 검토·제출 버퍼를 포함해 생성하는 마감 안전성 계획

두 계획은 동일한 슬롯 생성·의존성·우선순위 규칙을 사용한다. 차이는 필요한 작업 시간뿐이다.

### 2.4 슬롯

계획 엔진이 시간을 배정하는 최소 단위다. 기본값은 15분이다.

```text
slot_minutes = 15
```

모든 시간 추정과 일정 경계는 슬롯 단위로 올림한다.

### 2.5 유효 마감

`effective_deadline_at`는 계산에 실제로 사용하는 절대 시각이다. 원본 마감이 날짜만 있고 시각이 확인되지 않았다면 별도 규칙을 따른다.

### 2.6 동결 구간

현재 수행 중인 작업과 가까운 미래의 확정 계획을 자동 재배치하지 않는 구간이다.

```text
freeze_window_minutes = 120
```

Critical 위험을 해소하기 위해 변경이 불가피한 경우에도 사용자 승인이 필요하다.

---

## 3. Planner 입력 계약

Planner는 다음 입력을 명시적으로 받아야 하며 내부에서 현재 시각을 직접 읽으면 안 된다.

```text
PlannerInput
- planner_version
- now_utc
- user_timezone
- horizon_end_utc
- slot_minutes
- user_settings
- availability_windows
- calendar_events
- tasks
- milestones
- task_dependencies
- external_dependencies
- estimation_profiles
- prior_plan_snapshot
- permissions
- user_overrides
```

### 3.1 필수 검증

계산 전에 다음을 검증한다.

- 모든 ID가 Workspace 범위 안에 존재한다.
- 시작 시각은 종료 시각보다 이르다.
- `base_duration_minutes > 0`이다.
- `safety_duration_minutes >= base_duration_minutes`다.
- Done·Cancelled Task에는 잔여 시간이 없다.
- 모든 시각은 UTC로 저장되고 사용자 시간대 정보가 함께 존재한다.
- 동일한 외부 이벤트 ID가 둘 이상의 활성 일정에 연결되지 않는다.
- Hard Deadline 변경은 승인된 사실 상태에서만 입력된다.

검증 실패 시 Planner는 기존 정상 계획을 유지하고 `INVALID_INPUT`을 반환해야 한다.

### 3.2 입력 정규화

결정론성을 위해 다음 정규화를 수행한다.

- 모든 목록을 안정적인 키로 정렬한다.
- 문자열의 앞뒤 공백과 Unicode 정규화를 통일한다.
- 소수점 점수는 소수 넷째 자리에서 반올림한다.
- 모든 시간은 슬롯 경계로 올림 또는 내림한다.
- 동일 의미의 상태와 열거값은 Canonical Enum으로 변환한다.
- 입력 전체의 Canonical JSON으로 `input_hash`를 생성한다.

---

## 4. 시간과 날짜 규칙

### 4.1 저장 규칙

- 저장 시각은 UTC다.
- 원본 표현, 원본 시간대와 해석 근거를 함께 보존한다.
- 사용자 화면은 사용자 시간대로 변환한다.

### 4.2 상대 날짜

`다음 주 금요일`, `내일`, `이번 주말`은 입력이 발생한 절대 시각과 사용자 시간대를 기준으로 해석한다.

```text
raw_expression: "다음 주 금요일"
interpreted_date: 2026-08-28
interpretation_timezone: Asia/Seoul
interpretation_reference_at: 2026-08-23T03:02:15+09:00
```

### 4.3 날짜만 있고 시각이 없는 마감

마감 날짜는 확인됐지만 시각이 없으면 다음을 적용한다.

1. `deadline_date_known = true`
2. `deadline_time_known = false`
3. 임의로 23:59를 사실처럼 저장하면 안 된다.
4. 안전 계산의 임시 경계는 해당 날짜의 **00:00 로컬 시각**으로 둔다.
5. 위험 등급은 사용자 확인 전까지 Low가 될 수 없다.
6. 캘린더 쓰기와 제출 관련 자동 행동은 금지한다.
7. UI와 설명에 `마감 시각 미확인`을 반드시 표시한다.

이 규칙은 보수적으로 일찍 경고하기 위한 계산상 가정이며, 원본 사실을 변경하지 않는다.

### 4.4 요일·날짜 불일치

원본에 `8월 28일 목요일`처럼 날짜와 요일이 불일치하면 자동 등록하지 않는다. `Needs Confirmation` 상태로 보낸다.

---

## 5. 작업 시간 추정 규칙

### 5.1 기준 시간 보정

사용자별 동일 작업 유형의 실제 기록이 충분하면 보정 계수를 적용한다.

```text
adjusted_base = ceil_to_slot(
    raw_base_duration * estimation_profile_factor
)
```

초기 제한:

```text
0.75 <= estimation_profile_factor <= 2.50
```

표본 수에 따른 반영 강도:

- 0~2건: 계수 1.0 유지
- 3~5건: 관찰 계수의 30%만 반영
- 6~19건: 관찰 계수의 60% 반영
- 20건 이상: 관찰 계수의 80% 반영

### 5.2 안전 시간 계산

사용자가 별도 안전 시간을 확정하지 않았다면 다음 기본 배수를 적용한다.

```text
uncertainty = low    → 1.15
uncertainty = medium → 1.35
uncertainty = high   → 1.60
```

```text
safety_duration = ceil_to_slot(
    adjusted_base * uncertainty_multiplier
)
```

사용자가 확인한 안전 시간이 있으면 다음을 사용한다.

```text
safety_duration = max(
    user_confirmed_safety_duration,
    adjusted_base
)
```

### 5.3 집계 해석

개별 작업의 안전 시간을 합한 값은 프로젝트 전체의 통계적 P90이라고 표현하지 않는다. 다음 용어만 사용한다.

```text
총 기준 수요(Base Demand)
총 안전 수요(Safety Demand)
```

---

## 6. 의존성 그래프 규칙

### 6.1 방향

`A Blocks Start B`는 A가 완료되어야 B가 시작 가능하다는 뜻이다.

```text
A → B
```

`Blocks Completion`은 B의 작업 자체를 시작할 수 있으나 A 완료 전에는 B를 Done으로 전이할 수 없다는 뜻이다.

- 시간 슬롯 배정의 실행 가능 후보는 `Blocks Start`만으로 제한한다.
- `Blocks Completion`은 Task 상태 전이 검사에 적용한다.
- A 완료 이후 실제 추가 작업이 필요하면 이를 별도 Task로 만들고 `Blocks Start`를 사용한다.
- Planner가 숨은 추가 시간을 임의로 가정하면 안 된다.

`Related`는 순서 제약을 만들지 않는다.

### 6.2 사이클 탐지

Planner는 다음 두 그래프를 검증해야 한다.

1. `Blocks Start` 실행 그래프
2. `Blocks Start + Blocks Completion` 완료 가능성 그래프

두 그래프 중 하나라도 사이클이 있으면 Strongly Connected Components 또는 동등한 알고리즘으로 정확한 경로를 찾아야 한다.

사이클이 발견되면 다음을 수행한다.

- 관련 Task를 실행 계획에 배정하지 않는다.
- 관련 Task 상태 후보를 `Blocked: Dependency Cycle`로 표시한다.
- 위험 계산에서는 필요 작업량으로 유지한다.
- 사이클 경로를 사용자에게 보여준다.
- 자동으로 의존성을 삭제하거나 방향을 바꾸지 않는다.

```text
A → B → C → A
```

위 경우 Planner 결과에는 `DEPENDENCY_CYCLE` 오류와 `[A, B, C]`가 포함되어야 한다.

### 6.3 외부 의존성

외부 의존성에는 다음 필드가 필요하다.

```text
expected_delivery_at
uncertainty_buffer_minutes
fallback_available
fallback_task_ids
affected_task_ids
```

핵심 필드가 없으면 위험은 `Unknown`이다.

### 6.4 최종 안전 인계 시각

외부 결과가 가장 늦게 도착해도 전체 후행 작업과 검토 버퍼를 안전하게 완료할 수 있는 시각을 `latest_safe_handoff_at`으로 정의한다.

계산은 마일스톤의 유효 마감에서 역방향으로 수행한다. `Blocks Completion`은 추가 작업 시간이 없는 0분 완료 게이트로 반영한다. 실제 추가 시간이 필요하면 별도 Task가 존재해야 한다.

```text
latest_finish(task) = min(
    milestone_effective_deadline - mandatory_buffers,
    successors.latest_start
)

latest_start(task) = latest_finish(task) - task.safety_duration

latest_safe_handoff(external_dependency) =
    min(affected_tasks.latest_start)
```

외부 의존성 위험은 다음과 같이 판정한다.

- **Critical:** 현재 시각이 `latest_safe_handoff_at`을 지났고 대체 경로가 없음
- **High:** `expected_delivery_at > latest_safe_handoff_at`
- **Medium:** 전달 여유가 `uncertainty_buffer_minutes`보다 작거나 같음
- **Low:** 전달 여유가 불확실성 버퍼보다 큼
- **Unknown:** 전달 예상이나 후행 작업 추정이 없음

단순히 외부 의존성이 아직 완료되지 않았다는 이유만으로 Critical을 부여하면 안 된다.

### 6.5 역방향 임계 시각과 정렬 보조값

의존성 그래프가 유효하면 각 Task에 대해 마일스톤 마감에서 역방향으로 다음 값을 계산한다.

```text
latest_finish_at(task) = min(
    task_effective_deadline,
    successors.must_start_by_at
)

must_start_by_at(task) =
    latest_finish_at(task) - safety_duration_minutes
```

필수 버퍼 Synthetic Task도 같은 그래프에 포함한다. 외부 의존성으로 아직 시작할 수 없는 Task라도 `must_start_by_at`은 계산하여 위험과 확인 시점을 결정한다.

추가 보조값은 다음처럼 고정한다.

```text
critical_path_unlock_count =
    해당 Task가 완료될 때 새로 시작 가능해지는 미완료 후행 Task 수

context_switch_penalty =
    0: 현재 또는 직전 계획과 같은 Workstream
    1: 오늘 아직 활성 Workstream이 없음
    2: 다른 Workstream으로 전환

prior_plan_position =
    이전 Plan Snapshot의 오늘 큐 순번, 없으면 infinity
```

이 값은 입력과 그래프만으로 계산하며 LLM 판단을 사용하지 않는다.

---

## 7. 가용 시간 슬롯 생성

### 7.1 기본 생성 순서

각 날짜마다 다음 순서로 슬롯을 만든다.

1. 사용자 가용 시간 창 생성
2. 수면·수업·회의·고정 일정 제거
3. 이동·식사·휴식·전환 시간 제거
4. 이미 승인된 Focus Block 예약
5. 일일 계획 가능 비율 적용
6. 15분 슬롯으로 분할
7. Task별 장소·도구·에너지 적합성 태그 계산

### 7.2 일일 계획 가능 비율

```text
normal_condition  = 0.80
low_condition     = 0.65
crunch_condition  = 0.85
```

```text
planned_capacity = floor_to_slot(
    raw_free_minutes * capacity_factor
)
```

나머지 시간은 예기치 않은 지연과 회복 버퍼로 남긴다.

### 7.3 슬롯의 단일 소유권

하나의 슬롯은 다음 중 정확히 하나의 상태만 가질 수 있다.

```text
FREE
FIXED_EVENT
PROTECTED_FOCUS_BLOCK
TASK_ALLOCATION
BUFFER
```

`TASK_ALLOCATION` 슬롯은 둘 이상의 Task ID를 가질 수 없다. Base Pass와 Safety Pass는 별도 시뮬레이션이므로 서로 다른 결과 집합을 사용하지만, 한 Pass 안에서는 슬롯 중복이 절대 허용되지 않는다.

---

## 8. 제약조건

### 8.1 Hard Constraint

다음은 위반할 수 없다.

- Fixed Busy 일정과 겹치지 않음
- 같은 슬롯의 중복 사용 금지
- 시작 가능일 이전 배정 금지
- Blocks Start 선행조건 위반 금지
- 필요한 장소·도구 조건 위반 금지
- 사용자 제외일·제외 시간 위반 금지
- 사용자 고정 Task 이동 금지
- In Progress Task 자동 이동 금지
- 비분할 Task는 최소 연속 블록 확보
- Hard Deadline 이후 배정 금지
- 일일 최대 작업 시간 초과 금지
- 권한 정책 위반 금지

### 8.2 Soft Constraint

다음은 가능한 범위에서 최적화한다.

- 마감 위험 최소화
- 기존 계획 변경 최소화
- 프로젝트 전환 최소화
- 고집중 작업과 에너지 수준 일치
- 검토·제출 버퍼 확보
- 장기 중요 프로젝트 방치 방지
- 사용자의 선호 시간대 반영

Hard Constraint를 만족하지 못하는 계획을 사용자에게 확정 계획으로 제시하면 안 된다.

---

## 9. 우선순위 등급 규칙

### 9.0 두 단계 등급 확정

Base Pass 불가능 여부가 P0 판정에 영향을 주므로 등급은 다음 두 단계로 확정한다.

1. **초기 등급:** 마감 초과, 마감 유형, 사용자 중요도, Routine·Optional 여부로 P0 또는 P1~P4를 부여한다.
2. **Provisional Base Pass:** 초기 등급으로 전역 기준 계획을 한 번 생성한다.
3. **P0 승격:** Provisional Base Pass에서 필수 기준 시간이 미배정된 마일스톤의 필수 Task와 그 선행 병목을 P0로 승격한다.
4. **최종 Pass:** 승격된 최종 등급으로 Base Pass를 다시 한 번 실행하고, 같은 등급으로 Safety Pass를 실행한다.

P0 승격 반복은 한 번만 수행한다. 최종 Base Pass에서도 미배정이면 해당 마일스톤을 Critical로 판정한다.

### 9.1 P0 Rescue

다음 중 하나면 최종 P0다.

- 마감이 확정적으로 지났고 Task가 완료되지 않음
- Provisional Base Pass에서 필수 작업을 마감 전 모두 배정할 수 없음
- 오늘 시작하지 않으면 최종 Base Pass가 불가능해짐
- 핵심 외부 의존성이 `latest_safe_handoff_at`을 넘었고 대체 경로가 없음

### 9.2 P1 Protect

- Hard Deadline에 필요한 필수 Task
- External Commitment에 필요한 Task
- P0 또는 P1 Task의 선행 병목
- 필수 검토·제출 버퍼 Task

### 9.3 P2 Progress

- 사용자가 `반드시 보호` 또는 `중요`로 지정한 Workstream의 핵심 마일스톤 Task
- 주간 핵심 결과에 직접 연결된 Task
- 장기간 정체된 중요 Workstream의 다음 실행 Task

### 9.4 P3 Maintain

- 운동, 복습, 주간 회고 등 지속성 유지 Task
- 과부하 시 최소 수행량으로 축소 가능한 Routine 발생 항목

### 9.5 P4 Optional

- 추가 조사
- 선택 기능
- 디자인 개선
- 마감과 핵심 결과에 직접 영향이 없는 탐색 작업

---

## 10. 결정론적 정렬과 동률 처리

가중합 점수는 설명용으로만 사용할 수 있다. 실제 선택 순서는 다음 Tuple을 오름차순으로 비교한다.

```text
priority_key(task) = (
    priority_class_rank,              # P0=0 ... P4=4
    must_start_by_at_or_infinity,
    effective_deadline_at_or_infinity,
    -critical_path_unlock_count,
    -external_commitment_flag,
    -user_importance_rank,
    prior_plan_position_or_infinity,
    context_switch_penalty,
    created_at,
    task_id_lexicographic
)
```

추가 규칙:

- 동일 입력에서는 `task_id_lexicographic`까지 비교한다.
- LLM이 생성한 자연어 점수는 정렬 키로 사용하지 않는다.
- 현재 시각은 `PlannerInput.now_utc`만 사용한다.
- 시스템 난수는 사용하지 않는다.

---

## 11. 전역 용량 배정 알고리즘

### 11.1 두 번의 독립된 Pass

Planner는 동일 입력에 대해 다음 두 계획을 생성한다.

```text
Base Pass   → base_duration_minutes 사용
Safety Pass → safety_duration_minutes + mandatory buffer 사용
```

각 Pass는 가용 슬롯을 처음부터 새로 생성하여 독립적으로 실행한다.

### 11.2 Serial Schedule Generation

실제 실행 순서는 다음과 같다.

1. 입력과 그래프를 검증한다.
2. 유효한 Task와 Synthetic Buffer Task를 만든다.
3. 초기 P0~P4 등급을 부여한다.
4. 초기 등급으로 Provisional Base Pass를 실행한다.
5. 기준 시간이 미배정된 필수 경로를 P0로 승격한다.
6. 최종 등급으로 Base Pass를 다시 실행한다.
7. 같은 최종 등급으로 Safety Pass를 실행한다.

각 개별 Pass의 슬롯 배정은 다음 절차를 따른다.

1. 고정 일정과 보호된 기존 계획을 슬롯에 예약한다.
2. 현재 슬롯 시각에서 `Blocks Start`가 해소된 Task 집합을 만든다. `Blocks Completion`은 이 단계에서 시작을 막지 않는다.
3. `priority_key`가 가장 작은 Task를 선택한다.
4. 분할 가능 여부와 최소 블록을 확인한다.
5. 가능한 가장 이른 슬롯에 배정한다.
6. 해당 슬롯을 사용 처리한다.
7. Task 필요 시간이 충족되면 후행 Task를 후보로 해제한다.
8. 모든 슬롯 또는 모든 Task가 처리될 때까지 반복한다.

특정 비분할 Task가 현재 위치에 들어가지 않으면 해당 Task만 건너뛰고 다음 후보를 검사한다. 다른 Task가 사용할 수 있는 슬롯을 비워둔 채 전체 알고리즘을 중단하면 안 된다.

### 11.3 분할 가능한 Task

`splittable = true`면 다음을 만족하는 여러 블록으로 나눌 수 있다.

```text
각 블록 >= min_chunk_minutes
블록 수 <= max_chunks_per_day
```

기본값:

```text
min_chunk_minutes = 30
max_chunks_per_day = 3
```

### 11.4 비분할 Task

`splittable = false`면 `base_duration` 또는 `safety_duration` 전체를 수용하는 연속 슬롯이 있어야 한다. 연속 슬롯이 없으면 해당 Pass에서 미배정으로 남긴다.

### 11.5 필수 버퍼의 모델링

검토·테스트·제출 준비 시간은 추상적인 가산값이 아니라 별도의 Synthetic Task로 생성한다.

```text
REVIEW_BUFFER
TEST_BUFFER
SUBMISSION_BUFFER
```

이 Task는 P1이며 마일스톤의 Hard Deadline보다 앞선 내부 마감에 배정한다. 이렇게 해야 버퍼도 다른 Task와 동일한 공유 슬롯을 사용하며 중복 계산되지 않는다.

---

## 12. 마감별 용량과 위험 계산

### 12.1 전역 배정 결과가 기준

각 Task의 위험을 독립적으로 계산하지 않는다. 모든 Task가 동일한 슬롯 집합을 공유한 상태에서 Base Pass와 Safety Pass 배정 결과를 사용한다.

### 12.2 마일스톤 수요

```text
base_required_minutes =
    Σ remaining_base_minutes of required tasks

safety_required_minutes =
    Σ remaining_safety_minutes of required tasks
    + synthetic buffer minutes
```

### 12.3 배정량

```text
base_allocated_minutes =
    Base Pass에서 유효 마감 이전에 배정된 고유 슬롯 합계

safety_allocated_minutes =
    Safety Pass에서 유효 마감 이전에 배정된 고유 슬롯 합계
```

### 12.4 Coverage

```text
base_coverage = base_allocated_minutes / base_required_minutes
safety_coverage = safety_allocated_minutes / safety_required_minutes
```

분모가 0이면 Coverage는 1.0이다. Coverage는 반드시 전역 배정 후 계산하며, 각 작업이 같은 가용 시간을 중복 사용한 독립 계산값을 합치면 안 된다.

### 12.5 Slack

```text
if unallocated_required_minutes > 0:
    slack_minutes = -unallocated_required_minutes
else:
    slack_minutes = usable_free_slots_before_deadline_after_safety_pass
```

`usable_free_slots`는 해당 마일스톤의 필수 Task 중 최소 하나가 실제로 사용할 수 있는 아직 비어 있는 슬롯만 센다.

### 12.6 위험 등급 판정 순서

다음 순서를 위에서부터 적용한다.

#### Definitive Critical

정보 부족과 관계없이 다음 사실이 확정되면 Critical이다.

- 시각까지 확인된 마감이 지났고 필수 결과가 완료되지 않음
- 날짜만 확인된 마감의 **다음 로컬 날짜**가 되었는데 필수 결과가 완료되지 않음
- 외부 의존성이 `latest_safe_handoff_at`을 지났고 대체 경로가 없음
- 의존성 사이클 때문에 필수 경로를 시작할 수 없음

#### Unknown

- 마감 날짜 또는 필수 범위가 없음
- 기준 예상 시간 정보가 없음
- 날짜만 있고 시각이 확인되지 않음
- 필수 외부 의존성의 전달 예상이 없음

날짜만 있는 당일 마감은 계산상 00:00 경계를 사용하더라도 Base Pass 미배정을 이유로 Critical로 올리지 않고 Unknown으로 유지한다.

#### Capacity Critical

핵심 정보가 모두 확인된 상태에서 Base Pass Coverage < 1.0이면 Critical이다.

#### High

- Base Pass는 가능하지만 Safety Pass Coverage < 1.0
- 필수 검토·테스트·제출 버퍼가 모두 배정되지 않음
- 예상 외부 전달 시각이 `latest_safe_handoff_at`보다 늦음

#### Medium

Safety Pass가 가능하지만 다음 중 하나가 참이다.

```text
slack_minutes < max(30, ceil_to_slot(0.10 * safety_required_minutes))
```

또는 외부 의존성 전달 여유가 불확실성 버퍼 이하이다.

#### Low

- Base Pass와 Safety Pass Coverage가 모두 1.0
- 필수 버퍼가 전부 배정됨
- Medium 조건보다 큰 양의 Slack이 있음
- 핵심 정보가 모두 확인됨

### 12.7 마감 Prefix 검사

주간 총량만 확인하지 않는다. 서로 다른 모든 유효 마감 시각 `d1 < d2 < ... < dn`에 대해 해당 시각 이전에 필요한 Task 집합을 누적 검사한다.

각 Prefix의 배정은 동일한 전역 Pass 결과에서 읽는다. 따라서 하나의 슬롯이 여러 Prefix에서 보고될 수는 있지만 실제 Task 배정은 한 번뿐이다.

---

## 13. 오늘 계획 생성 규칙

### 13.1 오늘 계획의 기준

오늘 계획은 Base Pass의 오늘 배정을 기반으로 하되, Safety Pass에서 필요한 버퍼를 침범하지 않는다.

### 13.2 출력 구조

```text
오늘의 핵심 결과 1개
반드시 완료할 작업 1~3개
그다음 작업 큐
남는 시간에 할 작업
오늘 하지 않을 작업
위험과 승인 필요 변경
```

### 13.3 필수 규칙

- 오늘 총 배정 시간은 `planned_capacity`를 초과하지 않는다.
- P0·P1 미배정 수요가 있으면 P4를 오늘 계획에 넣지 않는다.
- `반드시 완료`에는 오늘 Base Pass에서 필요한 시간이 전부 배정된 Task만 넣는다.
- 현재 수행 중 Task는 첫 번째에 유지한다.
- 고집중 Workstream은 기본적으로 하루 최대 2개다.
- Routine은 P0·P1을 밀어내지 않는다.
- `오늘 하지 않을 일`에는 상위 후보였으나 용량 때문에 제외된 Task를 명시한다.

### 13.4 핵심 결과 선택

오늘의 핵심 결과는 다음 순서로 선택한다.

1. 오늘 완료 가능한 P0 Task가 만드는 결과
2. 오늘 완료 가능한 P1 마일스톤 결과
3. 주간 핵심 결과에 가장 큰 진척을 주는 P2 Task 묶음
4. 위 항목이 없으면 가장 오래 정체된 중요 Workstream의 검증 가능한 결과

추상적인 표현 대신 완료 조건이 있는 결과를 사용한다.

---

## 14. 재계획 규범

### 14.1 재계획 트리거

- 새 Hard Deadline
- 고정 일정 추가·변경
- 가용 시간 또는 컨디션 변경
- Task 완료·부분 완료·Blocked·Waiting
- 실제 시간이 예상보다 한 슬롯 이상 초과
- 외부 의존성 지연
- 사용자의 명시적 재계획 요청

단순 참고자료와 우선순위에 영향 없는 메모는 전체 재계획을 유발하지 않는다.

### 14.2 동결과 보호

- In Progress Task: 자동 이동 금지
- 사용자 고정 Task: 자동 이동 금지
- `now + 120분` 안의 확정 계획: 자동 이동 금지
- Fixed Event: 절대 이동 금지

Critical 위험을 해소할 유일한 방법이 동결 구간 변경이면 Proposal을 만들고 사용자 승인을 받아야 한다.

### 14.3 재계획 목적의 우선순위

재계획은 가중합 하나로 판단하지 않고 다음을 사전식으로 최소화한다.

```text
1. Hard Constraint 위반 수
2. 승인·권한 위반 수
3. Critical 마일스톤 수
4. Base Pass 미배정 총분
5. High 마일스톤 수
6. Safety Pass 미배정 총분
7. 기존 계획 변경 비용
8. 프로젝트 전환 수
9. 에너지·시간대 부적합 점수
```

앞 항목이 개선되지 않으면 뒤 항목의 이득으로 상쇄할 수 없다.

### 14.4 변경 비용

```text
In Progress 이동                    = 금지
Fixed Event 이동                    = 금지
사용자 Pin 이동                     = 금지
동결 구간 Task 이동                 = 1000
오늘 Task를 다른 날짜로 이동        = 40
오늘 계획에서 제거                  = 25
같은 날짜에서 2시간 이상 이동       = 10
같은 날짜에서 순서 한 칸 변경        = 2
새로운 유연 Task 추가                = 1
```

Critical 해결을 위해 높은 비용 변경이 필요하더라도 권한 정책을 우회하지 않는다.

---

## 15. 과부하 조정안 생성

Safety Pass가 불가능하면 다음 순서로 후보를 생성한다.

1. P4 제거
2. 이동 가능한 P3·낮은 P2 연기
3. 사용자가 승인할 수 있는 범위 축소안 생성
4. 외부 역할·일정·요구사항 조정 제안
5. 사용자 설정 최대치 안의 추가 시간 제안
6. 프로젝트 중단·포기 검토

각 Proposal에는 반드시 다음을 포함한다.

```text
before_state
proposed_state
minutes_saved_or_added
affected_milestones
new_base_coverage
new_safety_coverage
new_risk_level
approval_level
reversibility
```

서로 독립적인 조정안은 조합별로 시뮬레이션하여 실제로 위험이 얼마나 줄어드는지 계산한다.

---

## 16. 설명 데이터 계약

자연어 설명은 Planner의 구조화된 근거에서만 생성한다.

```text
DecisionEvidence
- selected_task_id
- priority_class
- effective_deadline_at
- base_coverage_before
- safety_coverage_before
- slack_minutes
- dependency_unlock_count
- external_commitment_flag
- capacity_conflicts
- excluded_task_ids
- changed_from_prior_plan
- planner_rule_ids
```

예시:

```text
데이터베이스 ERD 작성을 1순위로 선택했습니다.
- Hard Deadline까지 Base Pass가 60분 부족했습니다.
- 구현 Task 3개의 Blocks Start 선행 작업입니다.
- 오늘 배정 가능한 고집중 슬롯 90분과 일치합니다.
- 논문 정리는 P3이며 금요일로 이동해도 관련 마일스톤 위험이 Low로 유지됩니다.
```

LLM이 Planner 근거에 없는 이유를 추가하면 안 된다.

---

## 17. Planner 출력 계약

```text
PlannerOutput
- planner_version
- input_hash
- generated_at_utc
- base_plan
- safety_plan
- today_plan
- milestone_risks
- external_dependency_risks
- overloads
- proposals
- unresolved_items
- decision_evidence
- diff_from_prior_plan
- validation_warnings
```

각 Task Allocation에는 다음이 포함된다.

```text
- task_id
- start_at
- end_at
- pass_type
- chunk_index
- source_slot_ids
- allocation_reason_rule_ids
```

---

## 18. 참조 의사코드

```text
function plan(input):
    normalized = normalize_and_validate(input)
    if normalized.invalid:
        return INVALID_INPUT with prior_plan

    graph = build_dependency_graph(normalized)
    cycles = detect_cycles(graph)
    mark_cycle_tasks_blocked(cycles)

    slots = build_unique_slots(normalized)
    reserve_fixed_and_protected_slots(slots, normalized)

    tasks = derive_estimates_and_initial_priority_classes(normalized, graph)
    synthetic_buffers = create_mandatory_buffer_tasks(normalized)
    tasks = tasks + synthetic_buffers

    provisional_base = serial_schedule(
        tasks=tasks,
        slots=clone(slots),
        duration_field="base_duration_minutes",
        stable_priority_key=priority_key
    )

    tasks = promote_infeasible_required_paths_to_p0(
        tasks, provisional_base, graph
    )

    base_plan = serial_schedule(
        tasks=tasks,
        slots=clone(slots),
        duration_field="base_duration_minutes",
        stable_priority_key=priority_key
    )

    safety_plan = serial_schedule(
        tasks=tasks,
        slots=clone(slots),
        duration_field="safety_duration_minutes",
        stable_priority_key=priority_key
    )

    risks = calculate_risks_from_global_allocations(
        base_plan,
        safety_plan,
        normalized,
        graph
    )

    today = build_today_plan(base_plan, safety_plan, risks, normalized)

    candidate = minimize_replanning_lexicographically(
        today,
        prior_plan=normalized.prior_plan_snapshot,
        risks=risks,
        permissions=normalized.permissions
    )

    proposals = generate_overload_proposals_if_needed(candidate, risks)

    return build_output(
        normalized,
        base_plan,
        safety_plan,
        candidate,
        risks,
        proposals
    )
```

---

## 19. 필수 참조 테스트 벡터

### TV-01 공유 용량 중복 방지

```text
가용 시간: 오늘 4시간
Task A: 오늘 마감, 기준 4시간, P1
Task B: 오늘 마감, 기준 4시간, P1
```

기대 결과:

- Base Pass에서 총 4시간만 배정된다.
- A와 B가 각각 Coverage 1.0으로 계산되면 실패다.
- 안정적 동률 규칙에 따라 한 Task가 먼저 배정된다.
- 다른 Task는 Base 미배정 4시간이며 관련 마일스톤은 Critical이다.

### TV-02 결정론적 동률

입력과 시각이 동일한 동률 Task 3개를 100회 실행한다.

기대 결과:

- 모든 실행에서 동일한 Task 순서와 동일한 `input_hash` 기반 결과가 나온다.

### TV-03 의존성 사이클

```text
A Blocks Start B
B Blocks Start C
C Blocks Start A
```

기대 결과:

- 세 Task 모두 배정되지 않는다.
- `DEPENDENCY_CYCLE`과 정확한 사이클 경로가 반환된다.
- 관련 마감은 Low가 될 수 없다.

### TV-04 날짜만 있는 마감

```text
마감: 2026-09-10
시각: 미확인
```

기대 결과:

- `deadline_time_known=false`
- 임의의 23:59 사실 저장 금지
- 위험은 Low 불가
- 사용자 확인 항목 생성

### TV-05 외부 의존성 여유 있음

```text
expected_delivery_at < latest_safe_handoff_at - uncertainty_buffer
```

기대 결과:

- 외부 의존성이 미완료여도 Critical이 아니다.

### TV-06 외부 의존성 지연

```text
expected_delivery_at > latest_safe_handoff_at
fallback_available=false
```

기대 결과:

- 아직 최종 마감 전이어도 High
- 현재 시각이 latest_safe_handoff_at을 지나면 Critical

### TV-07 동결 구간

2시간 이내 확정 Task와 새 P2 Task가 충돌한다.

기대 결과:

- 확정 Task를 자동 이동하지 않는다.
- 새 Task는 이후 슬롯 또는 Proposal로 처리한다.

### TV-08 비분할 Task

```text
Task: 90분, splittable=false
가용 슬롯: 45분 + 45분, 중간에 회의
```

기대 결과:

- Task를 두 조각으로 배정하지 않는다.
- 미배정으로 남긴다.

### TV-09 Base 가능·Safety 불가능

```text
Base Demand 4시간
Safety Demand 6시간
가용 용량 5시간
```

기대 결과:

- Base Coverage 1.0
- Safety Coverage < 1.0
- 위험 High

### TV-10 최소 변경 재계획

기존 계획에서 오후 Task 하나만 이동하면 위험을 해소할 수 있다.

기대 결과:

- 전체 계획을 재생성하지 않는다.
- 변경 비용이 가장 낮은 한 Task만 이동한다.

### TV-11 Blocks Completion

```text
A Blocks Completion B
A 상태: Ready
B 상태: Ready
```

기대 결과:

- B 작업 슬롯은 계획할 수 있다.
- A가 Done이 되기 전 B의 Done 전이는 거부된다.
- A 완료 뒤 실제 추가 작업이 필요하다고 Planner가 임의 생성하지 않는다.

---

## 20. 구현 완료 조건

계획 엔진 구현은 다음을 모두 만족해야 완료로 판정한다.

- 필수 참조 테스트 벡터 100% 통과
- 속성 기반 테스트에서 슬롯 중복 0건
- 의존성 순서 위반 0건
- 동일 입력 반복 실행의 결과 불일치 0건
- 승인 없는 고정 일정·Hard Deadline 변경 0건
- Base·Safety Pass가 전역 공유 슬롯을 각각 한 번만 사용
- 위험 등급이 이 문서의 판정 순서를 그대로 따름
- 출력에 `planner_version`, `input_hash`, Rule ID 근거 포함
- 실패 시 마지막 정상 계획 유지

