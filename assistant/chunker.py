from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable

import tiktoken

from .config import SETTINGS
from .loader import Document

_ENCODER = tiktoken.get_encoding("cl100k_base")
_SENTENCE_RE = re.compile(r"(?<=[\.\!\?])\s+")


@dataclass
class Chunk:
    text: str
    metadata: dict
    chunk_id: str
    tokens: int


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text, disallowed_special=()))


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip()]


def _pack_units(units: list[str], target: int, overlap: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0

    for unit in units:
        ut = _count_tokens(unit)
        if ut > target and not current:
            chunks.append([unit])
            continue
        if current_tokens + ut > target and current:
            chunks.append(current)
            tail: list[str] = []
            tail_tokens = 0
            for u in reversed(current):
                ut2 = _count_tokens(u)
                if tail_tokens + ut2 > overlap and tail:
                    break
                tail.insert(0, u)
                tail_tokens += ut2
            current = tail
            current_tokens = tail_tokens
        current.append(unit)
        current_tokens += ut

    if current:
        chunks.append(current)
    return chunks


def _make_id(book: str, chapter: str, index: int, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    safe_book = re.sub(r"[^a-z0-9]+", "_", book.lower()).strip("_")
    safe_chapter = re.sub(r"[^a-z0-9]+", "_", chapter.lower()).strip("_")
    return f"{safe_book}__{safe_chapter}__p{index:04d}__{h}"


def chunk_document(doc: Document, target: int | None = None, overlap: int | None = None) -> list[Chunk]:
    target = target or SETTINGS.chunk_tokens
    overlap = overlap or SETTINGS.chunk_overlap
    paragraphs = _split_paragraphs(doc.content)
    if not paragraphs:
        return []

    units: list[str] = []
    for p in paragraphs:
        if _count_tokens(p) <= target:
            units.append(p)
        else:
            units.extend(_split_sentences(p))

    packed = _pack_units(units, target=target, overlap=overlap)
    out: list[Chunk] = []
    for i, group in enumerate(packed):
        text = "\n\n".join(group).strip()
        if not text:
            continue
        out.append(
            Chunk(
                text=text,
                metadata={
                    "book": doc.book,
                    "chapter": doc.chapter,
                    "title": doc.title,
                    "author": doc.author,
                    "position": i,
                    "file_path": doc.file_path,
                },
                chunk_id=_make_id(doc.book, doc.chapter, i, text),
                tokens=_count_tokens(text),
            )
        )
    return out


def chunk_documents(docs: Iterable[Document]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for d in docs:
        chunks.extend(chunk_document(d))
    return chunks
