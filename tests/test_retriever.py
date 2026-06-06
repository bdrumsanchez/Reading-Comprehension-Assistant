from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from assistant.chunker import chunk_document
from assistant.embedder import Embedder
from assistant.loader import Document, load_file
from assistant.retriever import Retriever
from assistant.store import VectorStore


def _build_doc(path: Path) -> Document:
    doc = load_file(path)
    doc.content_hash = "fixed-hash-for-test"
    return doc


def test_end_to_end_retrieve(tmp_path: Path) -> None:
    md = tmp_path / "sample.md"
    md.write_text(
        "---\nbook: t\nchapter: c\n---\n\n"
        "The lighthouse beam cut through the fog at midnight. "
        * 5
        + "\n\n"
        "Halden climbed the spiral staircase to the lens room. "
        * 5
        + "\n\n"
        "A small boat approached the rocky shore in silence. "
        * 5,
        encoding="utf-8",
    )
    doc = _build_doc(md)
    chunks = chunk_document(doc, target=80, overlap=20)
    assert chunks, "expected at least one chunk"

    class FakeEmbedder:
        dimension = 4

        def embed_cached(self, texts):
            rng = np.random.default_rng(0)
            return rng.random((len(texts), self.dimension)).astype(np.float32)

        def embed_query(self, text):
            v = np.zeros(self.dimension, dtype=np.float32)
            v[0] = 1.0
            return v

    embedder = FakeEmbedder()
    store = VectorStore(persist_dir=tmp_path / "chroma")
    store.add_chunks(doc.book, chunks, embedder.embed_cached([c.text for c in chunks]))

    retriever = Retriever(store, embedder=embedder)
    hits = retriever.retrieve(doc.book, "lighthouse")
    assert hits, "expected at least one hit"
    top = hits[0]
    assert "metadata" in top
    assert top["metadata"]["book"] == "t"


def test_persisted_chroma_path(tmp_path: Path) -> None:
    store = VectorStore(persist_dir=tmp_path / "chroma2")
    assert store.persist_dir.exists()
    assert store.list_books() == []
