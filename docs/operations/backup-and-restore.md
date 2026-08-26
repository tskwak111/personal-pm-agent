# Backup & Restore 운영 절차 (요약)

1. **백업**: 매일 `infra/backup/backup-postgres.sh` — age 공개키 암호화, 객체 저장소 업로드
2. **복원**: `infra/backup/restore-postgres.sh` — 복구 훈련은 분기 1회 스테이징에서 실시
3. **보존**: 원본 삭제 후 백업본은 30일 보존 뒤 파기(`RetentionVerifier` 계약)
4. **검증**: `scripts/test_backup_restore.py`가 카운트 일치·감사 링크 무결성을 확인
