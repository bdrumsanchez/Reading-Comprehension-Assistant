from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

CHAPTER_PREFIX_RE = re.compile(r"^\s*(\d+)[_\-\s]+(.*)$")
EXT_RE = re.compile(r"\.(txt|md|markdown)$", re.IGNORECASE)


@dataclass
class Document:
    book: str
    chapter: str
    title: str
    author: str
    content: str
    file_path: str
    content_hash: str
    extra: dict = field(default_factory=dict)


def _humanize(stem: str) -> str:
    cleaned = CHAPTER_PREFIX_RE.sub(r"\2", stem)
    cleaned = re.sub(r"[_\-]+", " ", cleaned).strip()
    return cleaned.replace("  ", " ")


def _detect_book(path: Path) -> str:
    parent = path.parent.name
    if parent and parent not in {".", "books", "data"}:
        return parent
    return path.stem


def _file_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_file(path: Path) -> Document:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if not EXT_RE.search(path.suffix):
        raise ValueError(f"Unsupported file type: {path.suffix} (use .txt or .md)")

    if path.suffix.lower() == ".md":
        post = frontmatter.load(path)
        meta = dict(post.metadata or {})
        content = post.content
    else:
        meta = {}
        content = path.read_text(encoding="utf-8")

    book = meta.get("book") or _detect_book(path)
    chapter = meta.get("chapter") or _humanize(path.stem)
    title = meta.get("title") or chapter
    author = meta.get("author", "")

    return Document(
        book=str(book),
        chapter=str(chapter),
        title=str(title),
        author=str(author),
        content=content.strip(),
        file_path=str(path.resolve()),
        content_hash=_file_hash(path),
        extra=meta,
    )


def discover_inputs(target: Path) -> list[Path]:
    target = Path(target)
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise FileNotFoundError(f"Not a file or directory: {target}")
    files: list[Path] = []
    for ext in ("*.md", "*.markdown", "*.txt"):
        files.extend(sorted(target.rglob(ext)))
    if not files:
        raise FileNotFoundError(f"No .txt or .md files found under {target}")
    return files
