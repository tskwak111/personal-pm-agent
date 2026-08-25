#!/usr/bin/env python3
"""Export FastAPI OpenAPI JSON for client generation."""

from __future__ import annotations

import json
from pathlib import Path

from personal_pm_api.main import create_app


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    app = create_app()
    openapi = app.openapi()
    target = out_dir / "openapi.json"
    target.write_text(json.dumps(openapi, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target} with {len(openapi.get('paths', {}))} paths")


if __name__ == "__main__":
    main()
