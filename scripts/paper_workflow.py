#!/usr/bin/env python3
"""One command surface for the literature workflow skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from build_paper_index import build_index
from find_paper import index_is_stale, score


ARXIV_ID_RE = re.compile(r"^(?P<id>\d{4}\.\d{4,5})(?P<version>v\d+)?$")
ARXIV_IN_TEXT_RE = re.compile(r"(?P<id>\d{4}\.\d{4,5})(?P<version>v\d+)?")
AMBIGUITY_MARGIN = 0.03
MIN_CONFIDENT_SCORE = 0.92
SOURCE_REGISTRY = Path("references/source_registry.jsonl")
SOURCE_KINDS = {"paper", "tech_doc", "spec", "blog", "repo", "dataset", "slides", "unknown"}
LOCAL_SOURCE_TYPES = {"pdf", "doc", "html", "text", "path"}


class WorkflowError(Exception):
    def __init__(self, code: str, message: str, details: object | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def note_filename(title: str) -> str:
    title = title.strip()
    if ":" in title:
        head = title.split(":", 1)[0].strip()
        if head and len(head.split()) <= 4 and (re.search(r"[A-Z]{2,}|[-_]", head) or head[:1].isupper()):
            title = head
    return f"{normalize(title)}.html"


def entity_id(title: str) -> str:
    return Path(note_filename(title)).stem


def ensure_root(root: Path) -> None:
    if not root.exists():
        raise WorkflowError("root_missing", f"workspace root does not exist: {root}")
    if not root.is_dir():
        raise WorkflowError("root_not_dir", f"workspace root is not a directory: {root}")


def write_index(root: Path) -> list[dict]:
    ensure_root(root)
    index = build_index(root, root / "references/references.bib")
    output = root / "references/paper_index.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in index) + "\n",
        encoding="utf-8",
    )
    return index


def read_index(root: Path) -> list[dict]:
    ensure_root(root)
    index_path = root / "references/paper_index.jsonl"
    if index_is_stale(root, index_path):
        write_index(root)
    try:
        lines = index_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError):
        write_index(root)
        lines = index_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]


def find_matches(root: Path, query: str, limit: int) -> list[dict]:
    if not query.strip():
        raise WorkflowError("empty_query", "paper query is empty")
    index = read_index(root)
    matches = sorted(
        ((score(query, item), item) for item in index),
        key=lambda pair: pair[0],
        reverse=True,
    )[:limit]
    return [{"score": round(value, 4), **item} for value, item in matches if value >= 0.45]


def resolve_pdf(root: Path, query: str) -> tuple[Path, dict | None]:
    path = Path(query).expanduser()
    if path.exists():
        return path.resolve(), None
    path = root / query
    if path.exists():
        return path.resolve(), None
    matches = find_matches(root, query, 5)
    if not matches:
        raise WorkflowError("no_match", f"no paper match: {query}")
    top = matches[0]
    if len(matches) > 1:
        second = matches[1]
        near_tie = top["score"] - second["score"] <= AMBIGUITY_MARGIN
        generic_query = len(re.sub(r"[^A-Za-z0-9]", "", query)) <= 4
        if top["score"] < MIN_CONFIDENT_SCORE or (top["score"] < 0.99 and (near_tie or generic_query)):
            raise WorkflowError("ambiguous_match", "paper query is ambiguous", matches)
    if not top.get("path"):
        raise WorkflowError("no_pdf_source", f"matched item has no local PDF source: {top.get('title', query)}", top)
    return (root / top["path"]).resolve(), top


def item_locator(item: dict) -> str:
    if item.get("path"):
        return str(item["path"])
    if item.get("sources"):
        source = item["sources"][0]
        if isinstance(source, dict):
            return str(source.get("locator") or "<no-local-pdf>")
    return str(item.get("primary_source") or "<no-local-pdf>")


def normalize_pdf_name(name: str) -> str:
    name = Path(name).name.strip() or "paper.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("._")
    return safe or "paper.pdf"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(2, 1000):
        candidate = path.with_name(f"{stem}_{idx}{suffix}")
        if not candidate.exists():
            return candidate
    raise WorkflowError("name_collision", f"too many existing files named like {path.name}")


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


def arxiv_pdf_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def resolve_add_source(source: str) -> tuple[str, str | None]:
    source = source.strip()
    if not source:
        raise WorkflowError("empty_source", "PDF source is empty")
    exact_arxiv = ARXIV_ID_RE.match(source)
    if exact_arxiv:
        arxiv_id = exact_arxiv.group(0)
        return arxiv_pdf_url(arxiv_id), f"{arxiv_id}.pdf"

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        match = ARXIV_IN_TEXT_RE.search(source)
        if parsed.netloc.endswith("arxiv.org") and match:
            arxiv_id = match.group(0)
            return arxiv_pdf_url(arxiv_id), f"{arxiv_id}.pdf"
        return source, normalize_pdf_name(Path(parsed.path).name)

    return str(Path(os.path.expanduser(source)).resolve()), None


def download(url: str, target: Path) -> None:
    request = Request(url, headers={"User-Agent": "literature-workflow-skill/1.0"})
    with urlopen(request, timeout=60) as response:
        target.write_bytes(response.read())


def add_pdf(root: Path, source: str, name: str | None = None) -> Path:
    ensure_root(root)
    resolved, inferred_name = resolve_add_source(source)
    parsed = urlparse(resolved)

    if parsed.scheme not in {"http", "https"}:
        src = Path(resolved)
        if not src.exists():
            raise WorkflowError("source_missing", f"source not found: {src}")
        if not src.is_file():
            raise WorkflowError("source_not_file", f"source is not a file: {src}")
        if not is_pdf(src):
            raise WorkflowError("source_not_pdf", f"source is not a PDF: {src}")
        try:
            src.relative_to(root)
            return src.resolve()
        except ValueError:
            pass

    filename = normalize_pdf_name(name or inferred_name or Path(resolved).name)
    target = unique_path(root / filename)

    if parsed.scheme in {"http", "https"}:
        try:
            download(resolved, target)
        except Exception as exc:
            raise WorkflowError("download_failed", f"failed to download PDF: {resolved}", str(exc)) from exc
    else:
        import shutil

        shutil.copy2(Path(resolved), target)

    if not is_pdf(target):
        target.unlink(missing_ok=True)
        raise WorkflowError("download_not_pdf", f"added file is not a valid PDF: {target}")
    return target


def source_registry_path(root: Path) -> Path:
    return root / SOURCE_REGISTRY


def load_source_records(root: Path) -> list[dict]:
    path = source_registry_path(root)
    if not path.exists():
        return []
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkflowError("invalid_source_registry", f"invalid JSON in {path}:{line_no}", str(exc)) from exc
        record.setdefault("id", entity_id(str(record.get("title", "untitled"))))
        record.setdefault("kind", "paper")
        record.setdefault("aliases", [])
        record.setdefault("sources", [])
        records.append(record)
    return records


def write_source_records(root: Path, records: list[dict]) -> None:
    path = source_registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def infer_source_type(locator: str) -> str:
    value = locator.strip()
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        if "github.com" in parsed.netloc:
            return "repo"
        if parsed.netloc.endswith("arxiv.org") or ARXIV_IN_TEXT_RE.search(value):
            return "arxiv"
        return "url"
    if ARXIV_ID_RE.match(value):
        return "arxiv"
    suffix = Path(value).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".md", ".txt", ".rst"}:
        return "text"
    return "path"


def normalize_source_locator(root: Path, locator: str, source_type: str) -> str:
    locator = locator.strip()
    if source_type in {"arxiv"}:
        match = ARXIV_IN_TEXT_RE.search(locator)
        return match.group(0) if match else locator.replace("arXiv:", "").strip()
    if source_type not in LOCAL_SOURCE_TYPES:
        return locator
    path = Path(os.path.expanduser(locator))
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def local_source_path(root: Path, locator: str, source_type: str) -> Path | None:
    if source_type not in LOCAL_SOURCE_TYPES:
        return None
    path = Path(os.path.expanduser(locator))
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def make_source(root: Path, locator: str, source_type: str | None = None, role: str = "supplement") -> dict:
    resolved_type = source_type or infer_source_type(locator)
    normalized = normalize_source_locator(root, locator, resolved_type)
    path = local_source_path(root, normalized, resolved_type)
    if resolved_type == "pdf" and path and path.exists() and not is_pdf(path):
        raise WorkflowError("source_not_pdf", f"source is not a PDF: {path}")
    status = "available" if path and path.exists() else ("missing" if path else "external")
    return {
        "type": resolved_type,
        "locator": normalized,
        "role": role,
        "status": status,
    }


def parse_typed_source(value: str) -> tuple[str | None, str]:
    if "=" not in value:
        return None, value
    source_type, locator = value.split("=", 1)
    source_type = source_type.strip().lower()
    if not source_type or not locator.strip():
        raise WorkflowError("invalid_source", "generic --source must be LOCATOR or type=LOCATOR")
    return source_type, locator.strip()


def collect_sources(args: argparse.Namespace) -> list[dict]:
    pairs: list[tuple[str | None, str]] = []
    for source_type in ("pdf", "url", "arxiv", "doi", "repo", "doc"):
        for locator in getattr(args, source_type, []) or []:
            pairs.append((source_type, locator))
    for value in getattr(args, "source", []) or []:
        pairs.append(parse_typed_source(value))

    sources = []
    for idx, (source_type, locator) in enumerate(pairs):
        role = "primary" if idx == 0 else "supplement"
        sources.append(make_source(args.root, locator, source_type, role))
    return sources


def source_key(source: dict) -> str:
    return f"{str(source.get('type', '')).lower()}:{str(source.get('locator', '')).strip().lower()}"


def merge_source_lists(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for source in [*existing, *incoming]:
        key = source_key(source)
        if key in seen:
            continue
        merged.append(source)
        seen.add(key)
    return merged


def record_aliases(record: dict) -> list[str]:
    aliases = [str(record.get("title", "")), str(record.get("id", ""))]
    aliases.extend(str(alias) for alias in record.get("aliases", []) if alias)
    for source in record.get("sources", []):
        locator = str(source.get("locator", ""))
        if locator:
            aliases.extend([locator, Path(locator).name, Path(locator).stem])
            if source.get("type") == "arxiv":
                aliases.append(f"arXiv:{locator}")
    return sorted({alias for alias in aliases if alias})


def registry_score_item(record: dict) -> dict:
    aliases = record_aliases(record)
    return {
        "title": record.get("title", ""),
        "aliases": aliases,
        "normalized_aliases": [re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip() for alias in aliases],
    }


def find_source_record(records: list[dict], query: str) -> tuple[int, dict] | tuple[None, None]:
    matches = sorted(
        ((score(query, registry_score_item(record)), idx, record) for idx, record in enumerate(records)),
        key=lambda item: item[0],
        reverse=True,
    )
    if not matches or matches[0][0] < 0.92:
        return None, None
    return matches[0][1], matches[0][2]


def record_from_index_item(item: dict) -> dict:
    return {
        "id": str(item.get("entity_id") or entity_id(str(item.get("title", "untitled")))),
        "kind": str(item.get("kind", "paper")),
        "title": str(item.get("title", "untitled")),
        "aliases": sorted(str(alias) for alias in item.get("aliases", []) if alias),
        "sources": item.get("sources") or (
            [{"type": "pdf", "locator": item["path"], "role": "primary", "status": "available"}]
            if item.get("path")
            else []
        ),
    }


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_extractor_status() -> dict[str, bool]:
    try:
        import pypdf  # noqa: F401

        pypdf = True
    except ImportError:
        pypdf = False
    try:
        import fitz  # noqa: F401

        pymupdf = True
    except ImportError:
        pymupdf = False
    return {
        "pypdf": pypdf,
        "pymupdf": pymupdf,
        "pdftotext": shutil.which("pdftotext") is not None,
    }


def extract_pdf_pages_with_pypdf(pdf_path: Path, max_pages: int | None) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise WorkflowError("text_extractor_missing", "Python package `pypdf` is not available") from exc

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        raise WorkflowError("pdf_read_failed", f"failed to read PDF: {pdf_path}", str(exc)) from exc
    pages = []
    selected = reader.pages if max_pages is None else reader.pages[:max_pages]
    for page in selected:
        pages.append(page.extract_text() or "")
    return pages


def extract_pdf_pages_with_pymupdf(pdf_path: Path, max_pages: int | None) -> list[str]:
    try:
        import fitz
    except ImportError as exc:
        raise WorkflowError("text_extractor_missing", "Python package `PyMuPDF` is not available") from exc

    try:
        doc = fitz.open(str(pdf_path))
        limit = len(doc) if max_pages is None else min(max_pages, len(doc))
        return [doc.load_page(idx).get_text() or "" for idx in range(limit)]
    except Exception as exc:
        raise WorkflowError("pdf_read_failed", f"failed to read PDF: {pdf_path}", str(exc)) from exc


def extract_pdf_pages_with_pdftotext(pdf_path: Path, max_pages: int | None) -> list[str]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise WorkflowError("text_extractor_missing", "system command `pdftotext` is not available")
    command = [pdftotext]
    if max_pages is not None:
        command.extend(["-f", "1", "-l", str(max_pages)])
    command.extend([str(pdf_path), "-"])
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise WorkflowError(
            "pdf_read_failed",
            f"failed to read PDF with pdftotext: {pdf_path}",
            {"stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:]},
        )
    pages = result.stdout.split("\f")
    return [page for page in pages if page.strip()]


def extract_pdf_pages(pdf_path: Path, max_pages: int | None = None) -> list[str]:
    status = text_extractor_status()
    if status["pypdf"]:
        return extract_pdf_pages_with_pypdf(pdf_path, max_pages)
    if status["pymupdf"]:
        return extract_pdf_pages_with_pymupdf(pdf_path, max_pages)
    if status["pdftotext"]:
        return extract_pdf_pages_with_pdftotext(pdf_path, max_pages)
    raise WorkflowError(
        "text_extractor_missing",
        "no PDF text extractor available; install pypdf, PyMuPDF, or poppler pdftotext",
        status,
    )


def extract_title_from_first_page(first_page: str, fallback: str) -> str:
    lines = [clean_text(line) for line in first_page.splitlines()]
    lines = [line for line in lines if line and not re.fullmatch(r"\d+", line)]
    if not lines:
        return fallback
    title = lines[0]
    for line in lines[1:4]:
        if "@" in line or re.search(r"\b(university|institute|college|school|department)\b", line, re.I):
            break
        candidate = f"{title} {line}"
        if len(candidate) > 220:
            break
        title = candidate
        if ":" in title and len(title) > 80:
            break
    return title


def between(text: str, start_pattern: str, end_pattern: str) -> str:
    start = re.search(start_pattern, text, flags=re.I | re.M)
    if not start:
        return ""
    end = re.search(end_pattern, text[start.end() :], flags=re.I | re.M)
    if not end:
        return clean_text(text[start.end() :])
    return clean_text(text[start.end() : start.end() + end.start()])


def readpack(root: Path, query: str, max_pages: int) -> dict:
    pdf_path, match = resolve_pdf(root, query)
    pages = extract_pdf_pages(pdf_path, max_pages=max_pages)
    full = "\n".join(pages)
    title = match.get("title") if match else extract_title_from_first_page(pages[0] if pages else "", pdf_path.stem)
    abstract = between(full, r"\bAbstract\b", r"\b(1\s+Introduction|Introduction|Keywords)\b")
    method = between(
        full,
        r"(^|\n)\s*(3\s+Methodology|Methodology|Method)\b",
        r"(^|\n)\s*(4\s+Experiments|Experiments|Evaluation|References|Appendix)\b",
    )
    appendix = between(full, r"(^|\n)\s*A\s+Instruction Templates\b", r"(^|\n)\s*B\s+")
    warnings = []
    if not abstract:
        warnings.append("abstract_not_found")
    if not method:
        warnings.append("method_not_found")
    return {
        "title": title,
        "path": str(pdf_path.relative_to(root) if pdf_path.is_relative_to(root) else pdf_path),
        "note_filename": note_filename(title),
        "abstract": abstract,
        "method_preview": method[:12000],
        "appendix_preview": appendix[:8000],
        "warnings": warnings,
    }


def renderer_status() -> dict[str, bool]:
    try:
        import fitz  # noqa: F401

        pymupdf = True
    except ImportError:
        pymupdf = False
    try:
        import PIL  # noqa: F401

        pil = True
    except ImportError:
        pil = False
    return {
        "ghostscript": shutil.which("gs") is not None,
        "pymupdf": pymupdf,
        "pdftoppm": shutil.which("pdftoppm") is not None,
        "pil": pil,
    }


def parse_crop(crop: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in crop.split(",")]
    if len(parts) != 4:
        raise WorkflowError("invalid_crop", "crop must be left,top,right,bottom")
    try:
        values = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise WorkflowError("invalid_crop", "crop coordinates must be integers") from exc
    left, top, right, bottom = values
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise WorkflowError("invalid_crop", "crop must satisfy 0 <= left < right and 0 <= top < bottom")
    return values


def render_page_with_ghostscript(pdf_path: Path, output: Path, page: int, dpi: int) -> None:
    gs = shutil.which("gs")
    if not gs:
        raise WorkflowError("pdf_renderer_missing", "Ghostscript is not available")
    command = [
        gs,
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=pngalpha",
        f"-r{dpi}",
        f"-dFirstPage={page}",
        f"-dLastPage={page}",
        f"-sOutputFile={output}",
        str(pdf_path),
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise WorkflowError(
            "pdf_render_failed",
            f"failed to render page {page} with Ghostscript",
            {"stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:]},
        )


def render_page_with_pymupdf(pdf_path: Path, output: Path, page: int, dpi: int) -> None:
    try:
        import fitz
    except ImportError as exc:
        raise WorkflowError("pdf_renderer_missing", "PyMuPDF is not available") from exc
    try:
        doc = fitz.open(str(pdf_path))
        if page < 1 or page > len(doc):
            raise WorkflowError("invalid_page", f"page {page} is outside 1..{len(doc)}")
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        pixmap = doc.load_page(page - 1).get_pixmap(matrix=matrix, alpha=True)
        pixmap.save(str(output))
    except WorkflowError:
        raise
    except Exception as exc:
        raise WorkflowError("pdf_render_failed", f"failed to render page {page} with PyMuPDF", str(exc)) from exc


def scale_crop(crop: str, scale: float) -> str:
    if scale == 1:
        return crop
    left, top, right, bottom = parse_crop(crop)
    scaled = (
        round(left * scale),
        round(top * scale),
        round(right * scale),
        round(bottom * scale),
    )
    return ",".join(str(value) for value in scaled)


def auto_render_dpi(pdf_path: Path, page: int, crop: str | None) -> int:
    base_dpi = 180
    max_dpi = 360
    if crop:
        left, top, right, bottom = parse_crop(crop)
        shortest_edge = min(right - left, bottom - top)
        if shortest_edge <= 0:
            return base_dpi
        target_shortest_edge = 1100
        scale = max(1.0, target_shortest_edge / shortest_edge)
        return min(max_dpi, max(base_dpi, int(round(base_dpi * scale / 30) * 30)))

    # Whole-page screenshots are usually used as contextual figures in notes.
    # A modest bump keeps small text readable without producing very large files.
    return 240


def parse_dpi(pdf_path: Path, page: int, dpi: str, crop: str | None) -> tuple[int, float, bool]:
    if dpi == "auto":
        resolved = auto_render_dpi(pdf_path, page, crop)
        return resolved, resolved / 180, True
    try:
        resolved = int(dpi)
    except ValueError as exc:
        raise WorkflowError("invalid_dpi", "dpi must be an integer between 36 and 600, or 'auto'") from exc
    if resolved < 36 or resolved > 600:
        raise WorkflowError("invalid_dpi", "dpi must be between 36 and 600")
    return resolved, 1.0, False


def crop_image(path: Path, crop: str) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise WorkflowError("image_crop_dependency_missing", "Pillow is required for --crop") from exc
    box = parse_crop(crop)
    with Image.open(path) as image:
        image.crop(box).save(path)


def render_page(root: Path, query: str, page: int, output: Path | None, dpi: str, crop: str | None) -> dict:
    if page < 1:
        raise WorkflowError("invalid_page", "page must be >= 1")
    pdf_path, match = resolve_pdf(root, query)
    resolved_dpi, crop_scale, dpi_auto = parse_dpi(pdf_path, page, dpi, crop)
    title = match.get("title") if match else pdf_path.stem
    if output is None:
        stem = Path(note_filename(title)).stem
        output = root / "notes/assets" / f"{stem}_page{page}.png"
    elif not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    status = renderer_status()
    if status["ghostscript"]:
        renderer = "ghostscript"
        render_page_with_ghostscript(pdf_path, output, page, resolved_dpi)
    elif status["pymupdf"]:
        renderer = "pymupdf"
        render_page_with_pymupdf(pdf_path, output, page, resolved_dpi)
    else:
        raise WorkflowError(
            "pdf_renderer_missing",
            "no PDF renderer available; install Ghostscript or PyMuPDF, or omit the screenshot",
            status,
        )
    if crop:
        crop_image(output, scale_crop(crop, crop_scale))
    return {
        "output": str(output.relative_to(root) if output.is_relative_to(root) else output),
        "paper": str(pdf_path.relative_to(root) if pdf_path.is_relative_to(root) else pdf_path),
        "page": page,
        "dpi": resolved_dpi,
        "dpi_auto": dpi_auto,
        "renderer": renderer,
        "cropped": bool(crop),
    }


def cmd_refresh(args: argparse.Namespace) -> int:
    index = write_index(args.root)
    print(f"wrote {len(index)} entries to references/paper_index.jsonl")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    matches = find_matches(args.root, args.query, args.limit)
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        for item in matches:
            kind = item.get("kind", "paper")
            print(f"{item['score']:.4f}\t{kind}\t{item_locator(item)}\t{item['title']}")
    return 0 if matches else 1


def cmd_add(args: argparse.Namespace) -> int:
    target = add_pdf(args.root, args.source, args.name)
    print(str(target.relative_to(args.root) if target.is_relative_to(args.root) else target))
    write_index(args.root)
    return 0


def cmd_readpack(args: argparse.Namespace) -> int:
    payload = readpack(args.root, args.query, args.max_pages)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_note_name(args: argparse.Namespace) -> int:
    print(note_filename(args.title))
    return 0


def cmd_render_page(args: argparse.Namespace) -> int:
    payload = render_page(args.root, args.query, args.page, args.output, args.dpi, args.crop)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    ensure_root(args.root)
    text_extractors = text_extractor_status()
    pdf_count = len(list((args.root / "papers").rglob("*.pdf"))) + len(list(args.root.glob("*.pdf")))
    index_path = args.root / "references/paper_index.jsonl"
    source_path = source_registry_path(args.root)
    status = {
        "root": str(args.root),
        "text_extractors": text_extractors,
        "renderers": renderer_status(),
        "pdf_count": pdf_count,
        "index_exists": index_path.exists(),
        "index_stale": index_is_stale(args.root, index_path),
        "bib_exists": (args.root / "references/references.bib").exists(),
        "source_registry_exists": source_path.exists(),
        "source_registry_records": len(load_source_records(args.root)) if source_path.exists() else 0,
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if any(text_extractors.values()) else 1


def cmd_source_init(args: argparse.Namespace) -> int:
    path = source_registry_path(args.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    print(str(path.relative_to(args.root)))
    return 0


def cmd_source_list(args: argparse.Namespace) -> int:
    records = load_source_records(args.root)
    if args.kind:
        records = [record for record in records if record.get("kind") == args.kind]
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        for record in records:
            print(f"{record.get('id')}\t{record.get('kind', 'paper')}\t{len(record.get('sources', []))}\t{record.get('title')}")
    return 0


def cmd_source_add(args: argparse.Namespace) -> int:
    if args.kind not in SOURCE_KINDS:
        raise WorkflowError("invalid_kind", f"kind must be one of: {', '.join(sorted(SOURCE_KINDS))}")
    records = load_source_records(args.root)
    record_id = args.id or entity_id(args.title)
    idx, existing = find_source_record(records, args.title)
    sources = collect_sources(args)
    aliases = sorted({*(args.alias or []), *(existing.get("aliases", []) if existing else [])})

    record = existing or {"id": record_id, "title": args.title, "kind": args.kind, "aliases": [], "sources": []}
    record["id"] = str(record.get("id") or record_id)
    record["title"] = args.title
    record["kind"] = args.kind
    record["aliases"] = aliases
    record["sources"] = merge_source_lists(record.get("sources", []), sources)

    if idx is None:
        records.append(record)
    else:
        records[idx] = record
    write_source_records(args.root, records)
    write_index(args.root)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def cmd_source_link(args: argparse.Namespace) -> int:
    records = load_source_records(args.root)
    idx, record = find_source_record(records, args.query)
    if record is None:
        matches = find_matches(args.root, args.query, 5)
        if not matches:
            raise WorkflowError("no_match", f"no entity match: {args.query}")
        if len(matches) > 1 and matches[0]["score"] - matches[1]["score"] <= AMBIGUITY_MARGIN:
            raise WorkflowError("ambiguous_match", "entity query is ambiguous", matches)
        record = record_from_index_item(matches[0])
        idx = None

    sources = collect_sources(args)
    if not sources:
        raise WorkflowError("empty_source", "no source was provided")
    record["sources"] = merge_source_lists(record.get("sources", []), sources)
    if args.alias:
        record["aliases"] = sorted({*record.get("aliases", []), *args.alias})

    if idx is None:
        records.append(record)
    else:
        records[idx] = record
    write_source_records(args.root, records)
    write_index(args.root)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def cmd_source_show(args: argparse.Namespace) -> int:
    matches = find_matches(args.root, args.query, args.limit)
    if not matches:
        raise WorkflowError("no_match", f"no entity match: {args.query}")
    print(json.dumps(matches, ensure_ascii=False, indent=2))
    return 0


def add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pdf", action="append", default=[], help="local PDF path")
    parser.add_argument("--url", action="append", default=[], help="web URL")
    parser.add_argument("--arxiv", action="append", default=[], help="arXiv id or URL")
    parser.add_argument("--doi", action="append", default=[], help="DOI")
    parser.add_argument("--repo", action="append", default=[], help="repository URL")
    parser.add_argument("--doc", action="append", default=[], help="local documentation path")
    parser.add_argument("--source", action="append", default=[], help="generic source, optionally type=locator")
    parser.add_argument("--alias", action="append", default=[], help="extra title or method alias")


def handle_error(exc: Exception) -> int:
    if isinstance(exc, WorkflowError):
        payload = {"ok": False, "error": exc.code, "message": exc.message}
        if exc.details is not None:
            payload["details"] = exc.details
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    raise exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Local literature workflow.")
    parser.add_argument("--root", default=".", type=Path, help="workspace root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    refresh = sub.add_parser("refresh", help="rebuild paper index")
    refresh.set_defaults(func=cmd_refresh)

    find = sub.add_parser("find", help="find a local PDF")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=5)
    find.add_argument("--json", action="store_true")
    find.set_defaults(func=cmd_find)

    add = sub.add_parser("add", help="add a PDF to the root inbox, then refresh index")
    add.add_argument("source")
    add.add_argument("--name")
    add.set_defaults(func=cmd_add)

    pack = sub.add_parser("readpack", help="resolve PDF and extract abstract/method snippets")
    pack.add_argument("query")
    pack.add_argument("--max-pages", type=int, default=12)
    pack.set_defaults(func=cmd_readpack)

    note = sub.add_parser("note-name", help="normalize title to HTML note filename")
    note.add_argument("title")
    note.set_defaults(func=cmd_note_name)

    render = sub.add_parser("render-page", help="render one PDF page to a PNG asset")
    render.add_argument("query")
    render.add_argument("--page", type=int, required=True)
    render.add_argument("--output", type=Path)
    render.add_argument("--dpi", default="180", help="integer DPI, or 'auto' for note-friendly rendering")
    render.add_argument("--crop", help="optional pixel crop: left,top,right,bottom")
    render.set_defaults(func=cmd_render_page)

    doctor = sub.add_parser("doctor", help="check workflow dependencies and index status")
    doctor.set_defaults(func=cmd_doctor)

    source = sub.add_parser("source", help="manage entity/source registry")
    source_sub = source.add_subparsers(dest="source_cmd", required=True)

    source_init = source_sub.add_parser("init", help="create references/source_registry.jsonl")
    source_init.set_defaults(func=cmd_source_init)

    source_list = source_sub.add_parser("list", help="list registered paper/doc entities")
    source_list.add_argument("--kind", choices=sorted(SOURCE_KINDS))
    source_list.add_argument("--json", action="store_true")
    source_list.set_defaults(func=cmd_source_list)

    source_add = source_sub.add_parser("add", help="register a paper, tech doc, repo, or other source entity")
    source_add.add_argument("--title", required=True)
    source_add.add_argument("--kind", default="paper", choices=sorted(SOURCE_KINDS))
    source_add.add_argument("--id")
    add_source_args(source_add)
    source_add.set_defaults(func=cmd_source_add)

    source_link = source_sub.add_parser("link", help="attach one or more sources to an existing entity")
    source_link.add_argument("query")
    add_source_args(source_link)
    source_link.set_defaults(func=cmd_source_link)

    source_show = source_sub.add_parser("show", help="show indexed source metadata for a query")
    source_show.add_argument("query")
    source_show.add_argument("--limit", type=int, default=5)
    source_show.set_defaults(func=cmd_source_show)

    args = parser.parse_args()
    args.root = args.root.resolve()
    try:
        return args.func(args)
    except Exception as exc:
        return handle_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
