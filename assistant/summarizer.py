from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .config import SUMMARY_CACHE_DIR
from .llm import LLM
from .loader import Document
from .prompts import (
    SYSTEM_DEFINE,
    SYSTEM_ELI5,
    SYSTEM_NOTES,
    SYSTEM_SUMMARIZER,
    chapter_user_prompt,
    concept_user_prompt,
    term_user_prompt,
)
from .retriever import Retriever


@dataclass
class GeneratedNote:
    text: str
    cached: bool


def _hash_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def _cache_path(key: str, mode: str) -> Path:
    safe_mode = mode.replace("/", "_")
    return SUMMARY_CACHE_DIR / f"{safe_mode}__{key[:16]}.json"


def _read_cache(key: str, mode: str) -> str | None:
    path = _cache_path(key, mode)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("text")
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(key: str, mode: str, text: str) -> None:
    path = _cache_path(key, mode)
    path.write_text(json.dumps({"text": text}), encoding="utf-8")


class Summarizer:
    def __init__(self, llm: LLM, retriever: Retriever | None = None) -> None:
        self.llm = llm
        self.retriever = retriever

    def summarize(self, doc: Document) -> GeneratedNote:
        key = _hash_key("summary", doc.content_hash)
        cached = _read_cache(key, "summary")
        if cached is not None:
            return GeneratedNote(text=cached, cached=True)
        label = f"{doc.book} / {doc.chapter}"
        prompt = chapter_user_prompt("Write a clear, faithful summary of this chapter.", label, doc.content)
        text = self.llm.complete(SYSTEM_SUMMARIZER, prompt)
        _write_cache(key, "summary", text)
        return GeneratedNote(text=text, cached=False)

    def notes(self, doc: Document) -> GeneratedNote:
        key = _hash_key("notes", doc.content_hash)
        cached = _read_cache(key, "notes")
        if cached is not None:
            return GeneratedNote(text=cached, cached=True)
        label = f"{doc.book} / {doc.chapter}"
        prompt = chapter_user_prompt(
            "Extract concise study notes with sections: Key Concepts, Vocabulary, Character & Plot Developments.",
            label,
            doc.content,
        )
        text = self.llm.complete(SYSTEM_NOTES, prompt)
        _write_cache(key, "notes", text)
        return GeneratedNote(text=text, cached=False)

    def define(self, book: str, term: str) -> GeneratedNote:
        assert self.retriever is not None, "Retriever required for term lookup"
        passages = self.retriever.retrieve(book, term)
        key = _hash_key("define", book, term, *(p["chunk_id"] for p in passages))
        cached = _read_cache(key, "define")
        if cached is not None:
            return GeneratedNote(text=cached, cached=True)
        user_prompt = term_user_prompt(term, passages)
        text = self.llm.complete(SYSTEM_DEFINE, user_prompt)
        _write_cache(key, "define", text)
        return GeneratedNote(text=text, cached=False)

    def eli5(self, book: str, concept: str) -> GeneratedNote:
        assert self.retriever is not None, "Retriever required for concept lookup"
        passages = self.retriever.retrieve(book, concept)
        key = _hash_key("eli5", book, concept, *(p["chunk_id"] for p in passages))
        cached = _read_cache(key, "eli5")
        if cached is not None:
            return GeneratedNote(text=cached, cached=True)
        user_prompt = concept_user_prompt(concept, passages)
        text = self.llm.complete(SYSTEM_ELI5, user_prompt)
        _write_cache(key, "eli5", text)
        return GeneratedNote(text=text, cached=False)
