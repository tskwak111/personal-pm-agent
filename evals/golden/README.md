# Golden Intake Dataset

Versioned JSONL cases for the AI metrics (AI-001..AI-015). Each line is one
`source_case.schema.json` document. The runner reports fixed denominators and
separates first-pass success (AI-001) from repaired success (AI-002).

Run:

```bash
uv run python scripts/run_intake_eval.py \
  --dataset evals/golden/fixtures/sample-cases.jsonl \
  --output evals/reports/intake-sample.json
```
