# Golden Intake Dataset

Versioned JSONL cases for the AI metrics (AI-001..AI-015). Each line is one
`source_case.schema.json` document. The runner reports fixed denominators and
separates first-pass success (AI-001) from repaired success (AI-002).

The repository contains only three synthetic fixtures. Stage B requires at
least 200 anonymized, independently labeled source records plus a complete
`counts.json`. Until those private records are supplied, `run_stage_b.py`
returns `BLOCKED_EXTERNAL` with process exit 2; fixtures are never counted as
release evidence by substitution.

Run:

```bash
uv run python scripts/run_intake_eval.py \
  --dataset evals/golden/fixtures/sample-cases.jsonl \
  --output evals/reports/intake-sample.json
```

Every non-empty JSONL line must have a unique `case_id`. Malformed records,
duplicate IDs, missing required metrics, and threshold failures are fatal.
