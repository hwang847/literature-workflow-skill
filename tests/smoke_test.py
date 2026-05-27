#!/usr/bin/env python3
"""Smoke-test the literature workflow skill without external dependencies."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "paper_workflow.py"
sys.path.insert(0, str(ROOT / "scripts"))

from paper_workflow import method_like_section, section_candidates  # noqa: E402


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
    sample_text = """
Abstract
This paper studies retrieval.

1 Introduction
Intro text.

2 Related Work
Prior systems.

3 GroupRAG Workflow
The workflow first builds a graph index from document chunks and entities. It then performs
community-aware retrieval, expands the query context with graph neighborhoods, and composes
evidence for generation. The controller keeps intermediate state, retrieved nodes, selected
communities, and final evidence passages so the answer can be traced through the pipeline.

4 Experiments
Results follow.
"""
    method, heading, label = method_like_section(sample_text)
    assert label == "workflow"
    assert heading == "3 GroupRAG Workflow"
    assert "community-aware retrieval" in method
    assert "3 GroupRAG Workflow" in section_candidates(sample_text)

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        setup = json.loads(run("--root", str(workspace), "setup").stdout)
        assert workspace.is_dir()
        assert (workspace / "papers").is_dir()
        assert (workspace / "notes" / "assets").is_dir()
        assert (workspace / "references" / "source_registry.jsonl").is_file()
        assert setup["index_entries"] == 0

        (workspace / "2501.00001v1.pdf").write_bytes(b"%PDF-1.4\n% smoke test placeholder\n")

        run("--root", str(workspace), "refresh")

        found = run("--root", str(workspace), "find", "2501.00001v1", "--json").stdout
        matches = json.loads(found)
        assert matches, "expected a PDF match"
        assert matches[0]["path"] == "2501.00001v1.pdf"

        registry = workspace / "references" / "source_registry.jsonl"
        registry.write_text(
            json.dumps(
                {
                    "title": "Human Friendly Title",
                    "kind": "paper",
                    "aliases": ["HFT"],
                    "sources": [
                        {
                            "type": "pdf",
                            "locator": "2501.00001v1.pdf",
                            "role": "primary",
                            "status": "available",
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        future = time.time() + 2
        os.utime(registry, (future, future))

        refreshed_by_registry = run("--root", str(workspace), "find", "HFT", "--json").stdout
        registry_matches = json.loads(refreshed_by_registry)
        assert registry_matches and registry_matches[0]["title"] == "Human Friendly Title"

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
