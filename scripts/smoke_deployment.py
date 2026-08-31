#!/usr/bin/env python3
"""Deployment smoke test: validate image and manifest contracts statically."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

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


def inspect_manifests(directory: Path) -> tuple[int, bool]:
    paths = sorted(directory.glob("*.yaml"))
    if len(paths) != 4:
        raise ValueError(f"expected 4 rendered manifest files, found {len(paths)}")
    documents = [doc for path in paths for doc in yaml.safe_load_all(path.read_text())]
    migration_separate = False
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("manifest document must be a mapping")
        kind = document.get("kind")
        spec = document.get("spec")
        if not isinstance(spec, dict):
            continue
        if kind == "Deployment":
            selector = spec.get("selector", {}).get("matchLabels")
            labels = spec.get("template", {}).get("metadata", {}).get("labels")
            if selector != labels or not selector:
                raise ValueError("Deployment selector must match pod labels")
        pod_spec = spec.get("template", {}).get("spec") if kind in {"Deployment", "Job"} else None
        if not isinstance(pod_spec, dict):
            continue
        if pod_spec.get("securityContext", {}).get("runAsNonRoot") is not True:
            raise ValueError(f"{kind} must run as non-root")
        for container in pod_spec.get("containers", []):
            image = str(container.get("image", ""))
            if re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image) is None:
                raise ValueError(f"mutable or invalid image reference: {image}")
            command = " ".join(str(item) for item in container.get("command", []))
            name = document.get("metadata", {}).get("name")
            if name == "pma-api" and "alembic" in command:
                raise ValueError("API process must not run migrations")
            if name == "pma-migrate" and "alembic" in command:
                migration_separate = True
    if not migration_separate:
        raise ValueError("migrate job missing alembic")
    return len(documents), migration_separate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-check deployment contract")
    parser.add_argument("--manifests", type=Path, required=True)
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

    try:
        document_count, migration_separate = inspect_manifests(args.manifests)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    payload = {
        "images": [
            {"name": i.name, "user": i.user, "has_cmd": i.has_healthcheck_or_cmd} for i in images
        ],
        "manifests": document_count,
        "migration_job_separate": migration_separate,
    }
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"deployment contract OK ({len(images)} images, {document_count} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
