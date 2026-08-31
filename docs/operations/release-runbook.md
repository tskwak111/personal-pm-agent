# 릴리스 런북 (요약)

1. `make verify` EXIT=0
2. Stage A/B/C 리포트 생성·확인 (`scripts/run_stage_{a,b,c}.py`)
3. 빌드·push 후 registry가 반환한 digest(`sha256:...`)를 사용해 manifest를 렌더링한다. tag나 `latest`는 허용하지 않는다.

   ```bash
   uv run python scripts/render_deployment.py \
     --api-digest "$API_IMAGE_DIGEST" \
     --worker-digest "$WORKER_IMAGE_DIGEST" \
     --web-digest "$WEB_IMAGE_DIGEST" \
     --output build/manifests
   uv run python scripts/smoke_deployment.py --manifests build/manifests
   ```

4. `pma-config`와 `pma-secrets`를 배포 환경에서 준비한다. secret 값을 저장소나 렌더 결과에 직접 넣지 않는다.
5. `migrate.yaml` Job을 먼저 실행하고 성공을 확인한 뒤 API, worker, web Deployment를 적용한다. API 시작 명령은 migration을 실행하지 않는다.
6. 백업/복원 훈련 결과 첨부 (`docs/operations/backup-and-restore.md`)
7. 파일럿 결과로 `scripts/verify_release.py` 게이트 결정 — **결정 이후 기준 변경 불가**
8. RISK_REGISTER 최종 갱신, S0/시스템 지연 0건 확인
