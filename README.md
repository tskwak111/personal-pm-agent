# Personal PM Agent

프로젝트·수업·과제·공모전·개인 공부가 동시에 진행될 때 사용자의 정리·우선순위 판단·과부하 협상·재계획 노동을 대신하는 개인 프로젝트 매니저 에이전트다.

## 핵심 제품 루프

```text
자연어·문서·이미지·캘린더
        ↓
통합 인박스와 출처 보존
        ↓
Planning Core 구조화
        ↓
결정론적 Base/Safety Planner
        ↓
오늘 계획·위험·과부하 Proposal
        ↓
승인·실행·검증·감사 기록
        ↓
실제 시간과 결과 기반 보정
```

## 핵심 차별점

- 사용자가 정리된 Task를 직접 만들어야 하는 일반 투두 앱과 달리 비정형 입력을 구조화한다.
- 각 Task가 같은 가용 시간을 중복 사용하지 않는 전역 용량 배정으로 마감 위험을 계산한다.
- 모든 일을 넣지 않고 연기·범위 축소·외부 조정·중단 후보를 협상한다.
- 새 정보가 들어와도 기존 계획을 최소한으로 바꾼다.
- 자동 변경은 이유, 권한 근거, 계획 버전과 되돌리기 정보를 가진다.
- LLM은 이해와 설명을 담당하고, 공식 상태와 산술 판단은 코드가 담당한다.

## 목표 기술 구조

```text
Next.js 16 + React 19 + TypeScript
                  ↓ REST / SSE
FastAPI Modular Monolith + Python 3.13
                  ↓
PostgreSQL 18 · Redis 8 · S3-compatible Object Storage
                  ↓
Worker · Google Calendar · Provider-independent LLM Gateway
```

정확한 패치 버전은 Phase 0에서 공식 릴리스와 호환성을 확인한 뒤 lockfile과 컨테이너 digest로 고정한다.

## 저장소 상태

이 패키지는 구현 전 최종 핸드오프 상태다. 현재 진행 상황은 `docs/status/IMPLEMENTATION_STATUS.md`를 기준으로 한다.

## 시작

`00_START_HERE.md`를 먼저 읽고 다음 명령을 실행한다.

```bash
python3 scripts/verify_package.py
```

## 개발 패키지 구성

- 승인된 상위 명세 3개
- 마스터 로드맵 1개와 Phase 구현계획 9개
- 안정적인 구현 Task ID 77개
- 요구사항 추적 항목 104개
- Gherkin 인수 시나리오 20개
- 출시 판정용 승인 지표 64개
- 상태 전이·권한·보안·운영·완료 기준 문서
- Codex 전체 개발·Phase 재개·최종 감사 프롬프트
- 패키지 검증 스크립트와 SHA-256 매니페스트
