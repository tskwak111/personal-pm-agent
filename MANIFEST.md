# Development Package Manifest

- **Package:** Personal PM Agent Final Development Package
- **Version:** 1.0.0
- **Manifest regenerated:** 2026-08-26T18:03:25+09:00
- **Product implementation status:** not started; this manifest verifies
  development-package artifacts only

## Package metrics

- Approved source specifications: 3
- Implementation Phases: 9
- TDD implementation Tasks: 77
- Traced requirements: 104
- Acceptance scenarios: 20
- Approved evaluation Metric IDs: 64

## Top-level inventory before manifest files

| Area | Files |
|---|---:|
| `00_START_HERE.md` | 1 |
| `AGENTS.md` | 1 |
| `PACKAGE_MANIFEST.md` | 1 |
| `PACKAGE_SUMMARY.json` | 1 |
| `README.md` | 1 |
| `SOURCE_SPEC_HASHES.sha256` | 1 |
| `docs` | 41 |
| `prompts` | 10 |
| `scripts` | 12 |

## File inventory before manifest files

| Path | Bytes | SHA-256 |
|---|---:|---|
| `00_START_HERE.md` | 5513 | `cb55176a25c1dcfa0a84914e2edd8ff8e032ae7b6582c329ae711b54beda7e92` |
| `AGENTS.md` | 6361 | `ceeb355938ee68285038189d740186fcf0a4bb31fa2f74ca3d8eab22789a9627` |
| `PACKAGE_MANIFEST.md` | 4501 | `648d631213b5961a9fe9a100e6c12142edbdc5d6b09df2e29dec826c1c26a312` |
| `PACKAGE_SUMMARY.json` | 811 | `1353ea998c3b515b25f5cbd3da1d360afbfc03fa52f726f587b2afd7cfc60626` |
| `README.md` | 2424 | `7b13ccef04b5ea0233900b1f51b43e1efd0e5d2eed4c96a09de84715f4511bd2` |
| `SOURCE_SPEC_HASHES.sha256` | 383 | `8e16c626cac19c95ac750c38a8eb815347cb21182490bae7ac53b4c917809ffa` |
| `docs/architecture/decision-precedence.md` | 2058 | `f049961e814843771faa17eabafd1e8051d3703b3d8b1db1ad1cd5c057c2c6d2` |
| `docs/architecture/domain-state-machines.md` | 6624 | `0d7f556ebf7d038366cb0421c344498630cca730c4601a93190d8c02fc6e1990` |
| `docs/architecture/engineering-standards.md` | 4030 | `e8815da6f970d88c070c464f311c2a5d16543feb97e1b71a85fd6b6df6b21115` |
| `docs/architecture/repository-and-module-contract.md` | 4165 | `5d6f67a04f1e2b554671d101245bb95931405343f103edd5ecfce8e4e75fe2f2` |
| `docs/architecture/toolchain-baseline.md` | 2476 | `1dcce647e77946e6595143e8bc237bed3fb569463effa7f1e5e8c50de84b4408` |
| `docs/operations/backup-and-restore.md` | 465 | `1a38b2b7b93a1aed23fbc987cec5904a394eb3cadd760c5b876452a0dead9dce` |
| `docs/operations/event-catalog.md` | 602 | `39a5aa927c325433307f218355ee17953e6404c9e211e49dfd7e291b5ef5a223` |
| `docs/operations/release-runbook.md` | 435 | `29b9ca5dce74165e093db87e656b08c24513dbc9249c63428bc63b7b04011100` |
| `docs/operations/security-privacy-and-runbook.md` | 4789 | `34ad3a9ba0cddffd9d9a87eb4280b7fdfc608d7d183fb621929ddb95936769e3` |
| `docs/pilot/annotation-guide.md` | 351 | `0e88e3d9c4732d96754a11c6f33533735dbd60fdfecebf50cb3f42d7713e446a` |
| `docs/pilot/baseline-questionnaire.md` | 196 | `946bcfb6273b0c4108cb395f944c26799846fbd82fc2a1b13e080173bb536518` |
| `docs/pilot/incident-procedure.md` | 329 | `0d1b8323003199ad0dce292df83da9abeec78145939994aacaa0cf4e626955b7` |
| `docs/pilot/participant-protocol.md` | 288 | `4f7472af4299dd5f5762827f18df1da8e4a10e43ccbc489b589a1a712717ec14` |
| `docs/pilot/weekly-survey.md` | 215 | `77034ae2ac6c28ef14fdb902f7b98b8b70c7f0557a846b09c558bc770a806aac` |
| `docs/plans/00-master-implementation-roadmap.md` | 9610 | `7a44de857adfd143c65bb5c654098062f5602ee0b344d074e9652544b18d7c68` |
| `docs/plans/01-phase-0-foundation.md` | 16689 | `cf79961f8831910e89834f71cd0b955fe75a6a068fe70e2ba1b04403e05ebf85` |
| `docs/plans/02-phase-1-domain-core.md` | 19883 | `4032c9769795cb7716c07b8e0ca47563c78fb59f2887e611400e64d9741c7133` |
| `docs/plans/03-phase-2-planner-engine.md` | 29827 | `3b54e9b6e4dd844383d83d5df6d68fdd9faf148056d5692a1fd2c018f62853ad` |
| `docs/plans/04-phase-3-persistence-api.md` | 26158 | `57b3061aa3bc94f7de015cfa937141773448bbf997b13e641bc07f64080c312e` |
| `docs/plans/05-phase-4-intake-llm-files.md` | 23990 | `cbdecd55eed29abbdf5c2726f7017379ba2e0192b418777c673137af7726522d` |
| `docs/plans/06-phase-5-calendar-execution.md` | 21616 | `3016a8cd11d853f1514f967c2c2845fe35cfe20419343f7133ac6ef45e6d6eb1` |
| `docs/plans/07-phase-6-agent-briefing.md` | 22851 | `2567dd7bd61367bfc2136652281d4e9738b75ed898d73dd17f022914090a92ea` |
| `docs/plans/08-phase-7-web-pwa.md` | 26853 | `30e80f9b909fa8582f831c959be7d7a28786063f74b2c75de5c11b7491d651ae` |
| `docs/plans/09-phase-8-evaluation-security-deployment.md` | 26882 | `2460312d6f8ee2091daacd953c8125e7cfa3231769f5d9a07bbb149b92f5d7e5` |
| `docs/quality/definition-of-done.md` | 2469 | `f3767b6339a7612630805e3a7f8934bca3b7c87da4f8100354f402e0c3cacd41` |
| `docs/quality/metric-gate-index.md` | 8826 | `5ef6b789df5c2e7da30a8f2483cd68403977015574fc0c5902e33a91c3953f7e` |
| `docs/quality/verification-command-matrix.md` | 2151 | `ef4ddc3267b3f63a936ad04e0128911fd40921aaaf82d8a4926a9e12338b934c` |
| `docs/requirements/acceptance-scenarios.md` | 7087 | `b2c59be7f7d3812fa5833ef99bd3c8c0b60861508d65be82d595ea2a1b1a0dac` |
| `docs/requirements/requirements-traceability.md` | 20825 | `da27db501687ff30c8ab87b29cadf6b01369c376be3e1939e5e8e4b5edf8c4bf` |
| `docs/specs/2026-08-23-personal-pm-agent-design.md` | 66469 | `0945e7681761d487bc2a25c3df66bf17ecab1ca3acab17a9eb0343613b7582e7` |
| `docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md` | 18086 | `c1c10711f737724dcf98f736ee941375ccb43e719c6d341446c19c760cad6afb` |
| `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md` | 33320 | `6679afb3e3f2bfdc0e39e1e24ce768eec7111c5a8fb76cfdebd038695a6e171f` |
| `docs/status/DECISION_LOG.md` | 4562 | `5de34ef6f73a0b5071ccdbda7c318f62e5b09565be615f1fff9db34fa5a5acad` |
| `docs/status/HANDOFF_CHECKLIST.md` | 705 | `60a813901e95c99e8863e13961a8ec40b29d59067ef92a96283110a533089167` |
| `docs/status/IMPLEMENTATION_STATUS.md` | 6246 | `c4bc2ea6cd7a43987aae5ded00297230e4fe8898cc7822841f575982aadf7d04` |
| `docs/status/RISK_REGISTER.md` | 2912 | `5279f9fcca7d9eb79a5a090e11ca68ed0078b3897a367036a7ea15bc3edd3a5d` |
| `docs/status/VERIFICATION_EVIDENCE.md` | 25016 | `761acdb6ca6ea16bc388628fa2ad19ef3b717d2ad508a7619d25fa539dc9af1d` |
| `docs/templates/ADR_TEMPLATE.md` | 579 | `b188a7e3787b79b29f571f30454aff736321660474cde2ff5a47207487c76e5c` |
| `docs/templates/INCIDENT_TEMPLATE.md` | 798 | `933138dc379f72c86ff28f641b4f5b50a4413a833219d980c164f467e6ca14d0` |
| `docs/templates/RELEASE_REPORT_TEMPLATE.md` | 717 | `c0e2355a50cadddc5f49b1a2f5c92462192508014382c5f4eb956c8bfe482948` |
| `docs/templates/TASK_COMPLETION_TEMPLATE.md` | 515 | `05efff7da4db318498ea124efa41f56110676097c0d0da185f32536af1f147f4` |
| `prompts/CODEX_FINAL_AUDIT_META_PROMPT.md` | 2344 | `eb41a078bad25b54c7e6045ff54e434f67e47c90cfa4755c707889fc1eee14c9` |
| `prompts/CODEX_MASTER_META_PROMPT.md` | 15914 | `fc8723dbace1a92cf6472f015c8278a9cd78792e827e9541edaed3581be40ff0` |
| `prompts/CODEX_PHASE_EXECUTION_PROMPT_TEMPLATE.md` | 1344 | `57028b9b515513a26c43cc3260462e83e379bdc63d3ef51e91f5e442be28bf52` |
| `prompts/CODEX_PHASE_PROMPTS.md` | 5380 | `672751ec8e1bc8cf326db5f66b2e088b4b1efd7e817128e548fc2d84695251da` |
| `prompts/CODEX_RESUME_PROMPT.md` | 1915 | `dfaccd6343e4a069dfd1312abc1371317f9e84d57803f5ddc085cde385373cba` |
| `prompts/CODE_REVIEW_PROMPT.md` | 2614 | `03785f9e40d1fa87bfae3e63c4c70d0a318d0ded276df998533c28e8baa50919` |
| `prompts/README.md` | 1332 | `2424412eb57776c961a4e5805e1425b21701f52aa3f139b73d2eed593b77d11d` |
| `prompts/RELEASE_AUDIT_PROMPT.md` | 2318 | `3e15e593dba6326a77049cd34d559aee4ccef4ce1f655420172bc5e63a583994` |
| `prompts/runtime/intake-structuring-v1.md` | 641 | `c35ea615685ffe73f47f43659f4a5d2098d4cfbb707bafa453216241aabe0176` |
| `prompts/runtime/project-decomposition-v1.md` | 594 | `b735e370c0baf75380065922534725e9325a39eb70183c668a3a31d42f02fa75` |
| `scripts/build_distribution_manifest.py` | 4044 | `715b4b50999d6f786cb278c91b1a7f24d5ad88884d58a3923330ed41dc4b77b2` |
| `scripts/export_openapi.py` | 643 | `fe562d7111652eef49eb06c1435437e47b72364ba77d24ef7d69b4872077febc` |
| `scripts/run_calendar_faults.py` | 6738 | `b757ac64ea9fa7403f7bf0874414e4f021e426f1866581135e6a1128d7259480` |
| `scripts/run_intake_eval.py` | 4275 | `d079f48f2c10c334437f2b7b29a4ff8ce1cd41eb4bfa78904aeb531d0f45e853` |
| `scripts/run_stage_a.py` | 4763 | `1167d9022dd8ea75f66e1bf603db93af5c52ac54504901dff33cb76be98e44eb` |
| `scripts/run_stage_b.py` | 2689 | `25a9252882fb55127be9f4757ef21843424247320dd5808eb91c263395fb2d5e` |
| `scripts/run_stage_c.py` | 3683 | `cf5b6304631470555597f1ac6ed9e011cb9c54a557c88bb55c65acecf707dd71` |
| `scripts/smoke_deployment.py` | 2409 | `5b57e949da4ae9090c748e6b62993a3f4a649fe1e160e54a7f72cc20d989918b` |
| `scripts/test_backup_restore.py` | 1728 | `d167968084e57674e2a92b2d15de6e15a73913b8d18a8512a25b966253633623` |
| `scripts/verify_package.py` | 14992 | `782724ca816d2f482974c33afaadf560a90d3f7b97bebe8b38632dc686e80e8c` |
| `scripts/verify_release.py` | 2971 | `95e66a4afe80eef9432215dc398e87f046c13df6521b60cdac66feefdda9c251` |
| `scripts/verify_repo.py` | 2056 | `f4f7066151bae4492ba5d0fddbb217e30afcae08606aca9fcaf1685049f38cca` |

## Verification

Run from the package root:

```bash
python3 scripts/verify_package.py

# Optional per-file checksum verification
sha256sum -c MANIFEST.sha256        # Linux
shasum -a 256 -c MANIFEST.sha256   # macOS
```

`MANIFEST.sha256` includes `MANIFEST.md` and every package file except itself,
Python bytecode and `__pycache__` artifacts.
