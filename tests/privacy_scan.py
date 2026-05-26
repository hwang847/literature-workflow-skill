#!/usr/bin/env python3
"""Scan release files for common private-path leaks."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".yaml",
    ".yml",
    ".txt",
    ".json",
    ".toml",
    ".sh",
    "",
}
DENY = (
    "/" + "Users/",
    "wang" + "haoran",
    "Desktop/" + "text2sql",
    ".codex/" + "RT" + "K.md",
    "@/" + "Users/",
)


def iter_files() -> list[Path]:
    ignored = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    files = []
    for path in ROOT.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix in TEXT_EXTENSIONS:
            files.append(path)
    return files


def main() -> int:
    leaks: list[str] = []
    for path in iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in DENY:
            if needle in text:
                leaks.append(f"{path.relative_to(ROOT)} contains {needle!r}")
    if leaks:
        print("\n".join(leaks))
        return 1
    print("privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
