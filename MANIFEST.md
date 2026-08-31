# Development Package Manifest

- **Package:** Personal PM Agent Final Development Package
- **Version:** 1.0.0
- **Manifest regenerated:** 2026-08-31T14:11:20+09:00
- **Product implementation status:** local implementation under final verification;
  release remains blocked on external evidence

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
| `docs` | 48 |
| `prompts` | 10 |
| `scripts` | 13 |

## File inventory before manifest files

| Path | Bytes | SHA-256 |
|---|---:|---|
| `00_START_HERE.md` | 5513 | `cb55176a25c1dcfa0a84914e2edd8ff8e032ae7b6582c329ae711b54beda7e92` |
| `AGENTS.md` | 6361 | `ceeb355938ee68285038189d740186fcf0a4bb31fa2f74ca3d8eab22789a9627` |
| `PACKAGE_MANIFEST.md` | 4501 | `648d631213b5961a9fe9a100e6c12142edbdc5d6b09df2e29dec826c1c26a312` |
| `PACKAGE_SUMMARY.json` | 828 | `f5f900593563e7001280a3d7f9723341880e6a3e1b7d6193f0bb829cd9570db7` |
| `README.md` | 2424 | `7b13ccef04b5ea0233900b1f51b43e1efd0e5d2eed4c96a09de84715f4511bd2` |
| `SOURCE_SPEC_HASHES.sha256` | 383 | `8e16c626cac19c95ac750c38a8eb815347cb21182490bae7ac53b4c917809ffa` |
| `docs/architecture/decision-precedence.md` | 2058 | `f049961e814843771faa17eabafd1e8051d3703b3d8b1db1ad1cd5c057c2c6d2` |
| `docs/architecture/domain-state-machines.md` | 6624 | `0d7f556ebf7d038366cb0421c344498630cca730c4601a93190d8c02fc6e1990` |
| `docs/architecture/engineering-standards.md` | 4030 | `e8815da6f970d88c070c464f311c2a5d16543feb97e1b71a85fd6b6df6b21115` |
| `docs/architecture/repository-and-module-contract.md` | 4165 | `5d6f67a04f1e2b554671d101245bb95931405343f103edd5ecfce8e4e75fe2f2` |
| `docs/architecture/toolchain-baseline.md` | 2476 | `1dcce647e77946e6595143e8bc237bed3fb569463effa7f1e5e8c50de84b4408` |
| `docs/operations/backup-and-restore.md` | 1851 | `977765aacca36f8ab730ddb206e69b4e442e2d2067bed50cbc861a32c29d7638` |
| `docs/operations/event-catalog.md` | 602 | `39a5aa927c325433307f218355ee17953e6404c9e211e49dfd7e291b5ef5a223` |
| `docs/operations/release-runbook.md` | 1137 | `11dcbe0cf3bb197ca2ebabbd62bbafda563a36b000ab593844a0da01d78969fe` |
| `docs/operations/security-privacy-and-runbook.md` | 5369 | `95007ce8d5c3c1a032854d761cbcb7ec5e95a641cf4dc4a87f464aff2ddca685` |
| `docs/pilot/annotation-guide.md` | 351 | `0e88e3d9c4732d96754a11c6f33533735dbd60fdfecebf50cb3f42d7713e446a` |
| `docs/pilot/baseline-questionnaire.md` | 196 | `946bcfb6273b0c4108cb395f944c26799846fbd82fc2a1b13e080173bb536518` |
| `docs/pilot/incident-procedure.md` | 329 | `0d1b8323003199ad0dce292df83da9abeec78145939994aacaa0cf4e626955b7` |
| `docs/pilot/participant-protocol.md` | 288 | `4f7472af4299dd5f5762827f18df1da8e4a10e43ccbc489b589a1a712717ec14` |
| `docs/pilot/weekly-survey.md` | 215 | `77034ae2ac6c28ef14fdb902f7b98b8b70c7f0557a846b09c558bc770a806aac` |
| `docs/plans/00-master-implementation-roadmap.md` | 9825 | `20863eb990d1635af99cfba2867af00dd76c2b3a4202545be73f3ea30d85b657` |
| `docs/plans/01-phase-0-foundation.md` | 16689 | `cf79961f8831910e89834f71cd0b955fe75a6a068fe70e2ba1b04403e05ebf85` |
| `docs/plans/02-phase-1-domain-core.md` | 19883 | `4032c9769795cb7716c07b8e0ca47563c78fb59f2887e611400e64d9741c7133` |
| `docs/plans/03-phase-2-planner-engine.md` | 29921 | `3ad1fee79676f4e8bf5ec7116c56c55ec2191c232910b4a8836fa026557d596b` |
| `docs/plans/04-phase-3-persistence-api.md` | 26158 | `0b69e990039cc77756d681c937b3da6f21e66bab8d90244c5a3cfc173d2cecf9` |
| `docs/plans/05-phase-4-intake-llm-files.md` | 23990 | `cbdecd55eed29abbdf5c2726f7017379ba2e0192b418777c673137af7726522d` |
| `docs/plans/06-phase-5-calendar-execution.md` | 21616 | `3016a8cd11d853f1514f967c2c2845fe35cfe20419343f7133ac6ef45e6d6eb1` |
| `docs/plans/07-phase-6-agent-briefing.md` | 22851 | `2567dd7bd61367bfc2136652281d4e9738b75ed898d73dd17f022914090a92ea` |
| `docs/plans/08-phase-7-web-pwa.md` | 26853 | `78f6b95e6c6b3ee904521ff8844d7747e57fd53211c819c37704417c556268be` |
| `docs/plans/09-phase-8-evaluation-security-deployment.md` | 27143 | `47eeed69ded68ff43dce907abd3ed03b3db72293d2860cd1eec262367ead5842` |
| `docs/quality/definition-of-done.md` | 2469 | `f3767b6339a7612630805e3a7f8934bca3b7c87da4f8100354f402e0c3cacd41` |
| `docs/quality/metric-gate-index.md` | 8826 | `5ef6b789df5c2e7da30a8f2483cd68403977015574fc0c5902e33a91c3953f7e` |
| `docs/quality/verification-command-matrix.md` | 2694 | `b8dbcaed28be5cbc21a2c060c01128fe6898531a1c283735c9d5f7d1f41b9da9` |
| `docs/requirements/acceptance-scenarios.md` | 7087 | `b2c59be7f7d3812fa5833ef99bd3c8c0b60861508d65be82d595ea2a1b1a0dac` |
| `docs/requirements/requirements-traceability.md` | 26307 | `3c12227cd777da919bc0a9f5dd1fa4e5fa7d59a437c45e8f2f20f12f327e01ba` |
| `docs/specs/2026-08-23-personal-pm-agent-design.md` | 66469 | `0945e7681761d487bc2a25c3df66bf17ecab1ca3acab17a9eb0343613b7582e7` |
| `docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md` | 18086 | `c1c10711f737724dcf98f736ee941375ccb43e719c6d341446c19c760cad6afb` |
| `docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md` | 33320 | `6679afb3e3f2bfdc0e39e1e24ce768eec7111c5a8fb76cfdebd038695a6e171f` |
| `docs/status/DECISION_LOG.md` | 6135 | `202244fe3e6c9b5ce507bf5872d9e095348a2e8b5c375aad064d7d856c87dafe` |
| `docs/status/HANDOFF_CHECKLIST.md` | 944 | `703fd0e888f10630c6f62c96a1bb0e39038e57e7c075bb86fec043e7b38dd5d9` |
| `docs/status/IMPLEMENTATION_STATUS.md` | 6991 | `d1ae9c6fb27a182d8cb158ad5dd8b00e7c4a2dfbf9295d77e91ad8fa6a1a5963` |
| `docs/status/RISK_REGISTER.md` | 3747 | `848f730efcea700478a21bd2eec23a1aac2dafe0bffd5a9755a0253f33674e33` |
| `docs/status/VERIFICATION_EVIDENCE.md` | 35825 | `a531d0896729a0959876fbf4052edef6f2644bfd3ca587bf712d8f18371df6b6` |
| `docs/superpowers/plans/2026-08-31-01-safety-planning-integrity.md` | 14912 | `b3b83a9de0a9ef432010a357165b33181aaaa1a2f84282bafd5fb0fb544e6195` |
| `docs/superpowers/plans/2026-08-31-02-truthful-release-gates.md` | 12246 | `a8463d0ee65229977a79d5b34ec5617de89d64132396e3352d48ad90172ec462` |
| `docs/superpowers/plans/2026-08-31-03-api-authorization-security.md` | 11415 | `e92f1712a1599a0977aa851ab7b802946379fa4a40320465ff0e9f8df977f992` |
| `docs/superpowers/plans/2026-08-31-04-web-openapi-pwa.md` | 12830 | `315e81399d58dee4e05e62a3f7755ac3d15b34c21def4b6faa30a2c0506a7998` |
| `docs/superpowers/plans/2026-08-31-05-runtime-deployment-observability.md` | 11327 | `1bf44f06f59b24a42e0053c95994afacce4cdb07bbd27da2db797c4a605f699c` |
| `docs/superpowers/plans/2026-08-31-06-traceability-cleanup-final-verification.md` | 10681 | `9777915da78054c263a5dffb02b29c85b87de5efb45e9ac9a650b40a25113aff` |
| `docs/superpowers/specs/2026-08-31-aaa-production-readiness-design.md` | 11012 | `c37c8954ed4c62fb3c7f8c0e0daf187381d12184cdaa4b512c8d1d47e53c0fcc` |
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
| `scripts/build_distribution_manifest.py` | 4065 | `c7eaff48f93a2e6f66a52107ff857941a8e94f4e8d193ea16a46640c2fbce179` |
| `scripts/export_openapi.py` | 643 | `fe562d7111652eef49eb06c1435437e47b72364ba77d24ef7d69b4872077febc` |
| `scripts/render_deployment.py` | 4214 | `2c325b390ffcb8115901dd474b1786411d8022036c5ffa1181b04fd507e379f5` |
| `scripts/run_calendar_faults.py` | 9382 | `bfc178d5285044d45d159ac356be440167100eb5c6ee1098acf12ba880828d04` |
| `scripts/run_intake_eval.py` | 4275 | `d079f48f2c10c334437f2b7b29a4ff8ce1cd41eb4bfa78904aeb531d0f45e853` |
| `scripts/run_stage_a.py` | 9806 | `20e3d6141d2ab0baa7bdd2676330dfc2ba2e5cafacdb4ae79c89a7db49a51df5` |
| `scripts/run_stage_b.py` | 6978 | `4400865f55f93f6a459cd6334439556b0970c44dba5d0ab65890914f04896250` |
| `scripts/run_stage_c.py` | 5168 | `61da0f949cacd19e05fa1700627d7f19abff1552af67d3616b1ea9f0d59fb957` |
| `scripts/smoke_deployment.py` | 4276 | `121615c73b8bc7b0afd0c3d4d39d8fd1d4e8f31f6bdb36347ed7b2cb2b1b715d` |
| `scripts/test_backup_restore.py` | 6769 | `1d695eb95dee15781969a1beeb7ef648c961f007b49b051cabe7494a5a717c45` |
| `scripts/verify_package.py` | 14992 | `782724ca816d2f482974c33afaadf560a90d3f7b97bebe8b38632dc686e80e8c` |
| `scripts/verify_release.py` | 8822 | `ded34bbb84e82609223915080a69336a1bbaa967abbf9a0c6921fa694989f683` |
| `scripts/verify_repo.py` | 6293 | `f8888743704bcf56945e8fb53564922497f39878bcb0400e8ad02cf279b0a5b7` |

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
