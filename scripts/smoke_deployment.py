#!/usr/bin/env python3
"""Deployment smoke test: validate image and manifest contracts statically."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

USER_LINE = re.compile(r"^USER\s+(\S+)", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ImageContract:
    name: str
    user: str
    has_healthcheck_or_cmd: bool


def validate_image_contract(image: ImageContract) -> ImageContract:
    """Raise when an image would run as root."""
    if image.user in {"", "0", "root"}:
        raise ValueError(f"image {image.name} runs as root")
    return image


def inspect_dockerfile(path: Path) -> ImageContract:
    source = path.read_text(encoding="utf-8")
    match = USER_LINE.search(source)
    return ImageContract(
        name=path.stem.replace("Dockerfile.", ""),
        user=match.group(1) if match else "",
        has_healthcheck_or_cmd="CMD" in source,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-check deployment contract")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    docker_dir = Path("infra/docker")
    images = [inspect_dockerfile(p) for p in sorted(docker_dir.glob("Dockerfile.*"))]
    for image in images:
        try:
            validate_image_contract(image)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    # Migration must be a separate job from the API process.
    api_yaml = Path("infra/deployment/api.yaml").read_text(encoding="utf-8")
    migrate_yaml = Path("infra/deployment/migrate.yaml").read_text(encoding="utf-8")
    if "alembic" in api_yaml:
        print("FAIL: API process must not run migrations", file=sys.stderr)
        return 1
    if "alembic" not in migrate_yaml:
        print("FAIL: migrate job missing alembic", file=sys.stderr)
        return 1

    payload = {
        "images": [
            {"name": i.name, "user": i.user, "has_cmd": i.has_healthcheck_or_cmd} for i in images
        ],
        "migration_job_separate": True,
    }
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"deployment contract OK ({len(images)} images)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
