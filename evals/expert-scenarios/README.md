# Expert Planning Scenarios

Stage B requires at least 150 privately reviewed JSONL scenarios. Each record
must have a unique `scenario_id` and cover feasibility, risk class, protected
tasks, unallocated work, approval type, and the minimum acceptable replan.

The repository contains only two synthetic fixtures; private reviewed data is
intentionally absent. The resulting shortfall is `BLOCKED_EXTERNAL` with exit
2, never PASS. A complete `evals/golden/counts.json` must include every metric
required by `scripts/run_stage_b.py` before release evaluation can proceed.
