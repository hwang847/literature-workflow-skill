#!/usr/bin/env python3
"""Smoke-test the literature workflow skill without external dependencies."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "paper_workflow.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-B", str(TOOL), *args],
        cwd=str(cwd or ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "papers").mkdir()
        (workspace / "notes").mkdir()
        (workspace / "references").mkdir()
        (workspace / "2501.00001v1.pdf").write_bytes(b"%PDF-1.4\n% smoke test placeholder\n")

        run("--root", str(workspace), "refresh")

        found = run("--root", str(workspace), "find", "2501.00001v1", "--json").stdout
        matches = json.loads(found)
        assert matches, "expected a PDF match"
        assert matches[0]["path"] == "2501.00001v1.pdf"

        note_name = run("--root", str(workspace), "note-name", "LinkAlign: Example Paper").stdout.strip()
        assert note_name == "linkalign.html"

        run(
            "--root",
            str(workspace),
            "source",
            "add",
            "--kind",
            "tech_doc",
            "--title",
            "Example System Documentation",
            "--url",
            "https://example.com/docs",
            "--repo",
            "https://github.com/example/project",
            "--alias",
            "ESD",
        )

        shown = run("--root", str(workspace), "source", "show", "ESD").stdout
        items = json.loads(shown)
        assert items and items[0]["kind"] == "tech_doc"
        assert items[0]["source_count"] == 2

    print("smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
