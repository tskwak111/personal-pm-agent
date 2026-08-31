#!/usr/bin/env python3
"""Render deployment templates only from immutable image digests."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
IMAGES = {
    "@@API_IMAGE@@": "ghcr.io/personal-pm/api",
    "@@WORKER_IMAGE@@": "ghcr.io/personal-pm/worker",
    "@@WEB_IMAGE@@": "ghcr.io/personal-pm/web",
}


@dataclass(frozen=True, slots=True)
class RenderedDeployment:
    files: tuple[Path, ...]
    documents: tuple[dict[str, Any], ...]


def _image(name: str, digest: str) -> str:
    if DIGEST.fullmatch(digest) is None:
        raise ValueError(f"{name} digest must match sha256:<64 lowercase hex>")
    return f"{name}@{digest}"


def _validate_document(document: object, source: Path) -> dict[str, Any]:
    if not isinstance(document, dict) or not all(
        isinstance(document.get(key), str) for key in ("apiVersion", "kind")
    ):
        raise ValueError(f"invalid Kubernetes document in {source}")
    metadata = document.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("name"), str):
        raise ValueError(f"missing metadata.name in {source}")
    if document["kind"] == "Deployment":
        spec = document.get("spec")
        if not isinstance(spec, dict):
            raise ValueError(f"missing Deployment spec in {source}")
        selector = spec.get("selector")
        template = spec.get("template")
        if not isinstance(selector, dict) or not isinstance(template, dict):
            raise ValueError(f"missing Deployment selector/template in {source}")
        template_metadata = template.get("metadata")
        if not isinstance(template_metadata, dict) or selector.get(
            "matchLabels"
        ) != template_metadata.get("labels"):
            raise ValueError(f"Deployment selector does not match pod labels in {source}")
    return document


def render_all(
    *,
    api_digest: str,
    worker_digest: str,
    web_digest: str,
    output: Path,
    template_dir: Path = Path("infra/deployment"),
) -> RenderedDeployment:
    replacements = {
        "@@API_IMAGE@@": _image(IMAGES["@@API_IMAGE@@"], api_digest),
        "@@WORKER_IMAGE@@": _image(IMAGES["@@WORKER_IMAGE@@"], worker_digest),
        "@@WEB_IMAGE@@": _image(IMAGES["@@WEB_IMAGE@@"], web_digest),
    }
    rendered: list[tuple[Path, str]] = []
    documents: list[dict[str, Any]] = []
    for template in sorted(template_dir.glob("*.yaml.tmpl")):
        source = template.read_text(encoding="utf-8")
        for marker, image in replacements.items():
            source = source.replace(marker, image)
        if "@@" in source or ":latest" in source:
            raise ValueError(f"unresolved or mutable image reference in {template}")
        parsed = [_validate_document(doc, template) for doc in yaml.safe_load_all(source)]
        if not parsed:
            raise ValueError(f"empty deployment template {template}")
        rendered.append((output / template.name.removesuffix(".tmpl"), source))
        documents.extend(parsed)
    if len(rendered) != 4:
        raise ValueError(f"expected 4 deployment templates, found {len(rendered)}")

    output.mkdir(parents=True, exist_ok=True)
    for target, source in rendered:
        target.write_text(source, encoding="utf-8")
    return RenderedDeployment(
        files=tuple(target for target, _ in rendered),
        documents=tuple(documents),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-digest", required=True)
    parser.add_argument("--worker-digest", required=True)
    parser.add_argument("--web-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = render_all(
        api_digest=args.api_digest,
        worker_digest=args.worker_digest,
        web_digest=args.web_digest,
        output=args.output,
    )
    print(f"rendered {len(result.files)} deployment files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
