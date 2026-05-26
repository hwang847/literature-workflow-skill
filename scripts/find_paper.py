#!/usr/bin/env python3
"""Find a local paper PDF by copied title, alias, arXiv id, or filename."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def library_pdfs(root: Path) -> list[Path]:
    paths = list((root / "papers").rglob("*.pdf"))
    paths.extend(sorted(root.glob("*.pdf")))
    return paths


def index_is_stale(root: Path, index_path: Path) -> bool:
    if not index_path.exists():
        return True
    index_mtime = index_path.stat().st_mtime
    return any(path.stat().st_mtime > index_mtime for path in library_pdfs(root))


def load_index(root: Path, index_path: Path) -> list[dict]:
    if index_is_stale(root, index_path):
        script_dir = Path(__file__).resolve().parent
        subprocess.run(
            [sys.executable, str(script_dir / "build_paper_index.py"), "--root", str(root)],
            check=True,
        )
    return [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(query: str, item: dict) -> float:
    q = normalize(query)
    aliases = item.get("normalized_aliases") or [normalize(item.get("title", ""))]
    best = 0.0
    for alias in aliases:
        if not alias:
            continue
        if q == alias:
            best = max(best, 1.0)
        elif q in alias or alias in q:
            best = max(best, 0.94)
        else:
            best = max(best, difflib.SequenceMatcher(None, q, alias).ratio())
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Find a paper in references/paper_index.jsonl.")
    parser.add_argument("query", help="copied title, method name, arXiv id, or filename")
    parser.add_argument("--root", default=".", help="literature workspace root")
    parser.add_argument("--index", default="references/paper_index.jsonl", help="JSONL index path")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index = load_index(root, root / args.index)
    matches = sorted(
        ((score(args.query, item), item) for item in index),
        key=lambda pair: pair[0],
        reverse=True,
    )[: args.limit]
    matches = [{"score": round(value, 4), **item} for value, item in matches if value >= 0.45]

    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        for item in matches:
            print(f"{item['score']:.4f}\t{item['path']}\t{item['title']}")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
