# 릴리스 런북 (요약)

1. `make verify` EXIT=0
2. Stage A/B/C 리포트 생성·확인 (`scripts/run_stage_{a,b,c}.py`)
3. `scripts/smoke_deployment.py` 배포 계약 확인
4. 백업/복원 훈련 결과 첨부 (`docs/operations/backup-and-restore.md`)
5. 파일럿 결과로 `scripts/verify_release.py` 게이트 결정 — **결정 이후 기준 변경 불가**
6. RISK_REGISTER 최종 갱신, S0/시스템 지연 0건 확인
