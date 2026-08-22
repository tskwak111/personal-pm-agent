from pathlib import Path

REQUIRED = {
    ".python-version": "3.13",
    ".node-version": "24",
    "package.json": '"packageManager"',
    "pyproject.toml": "[tool.uv.workspace]",
    "Makefile": "verify:",
}


def test_root_contract_files_and_markers_exist() -> None:
    for name, marker in REQUIRED.items():
        text = Path(name).read_text(encoding="utf-8")
        assert marker in text, (name, marker)
