from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from numpy.typing import NDArray

from .chunker import Chunk
from .config import CHROMA_DIR, SETTINGS


class VectorStore:
    def __init__(self, persist_dir: Path | None = None) -> None:
        self.persist_dir = Path(persist_dir or CHROMA_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    @staticmethod
    def _collection_name(book: str) -> str:
        import re

        safe = re.sub(r"[^a-z0-9]+", "_", book.lower()).strip("_")
        return f"book_{safe}" or "book_default"

    def get_or_create(self, book: str):
        return self._client.get_or_create_collection(
            name=self._collection_name(book),
            metadata={"book": book},
        )

    def delete_book(self, book: str) -> None:
        try:
            self._client.delete_collection(self._collection_name(book))
        except Exception:
            pass

    def list_books(self) -> list[str]:
        out: list[str] = []
        for c in self._client.list_collections():
            meta = c.metadata or {}
            if "book" in meta:
                out.append(meta["book"])
        return sorted(out)

    def add_chunks(
        self,
        book: str,
        chunks: list[Chunk],
        embeddings: NDArray,
    ) -> None:
        if not chunks:
            return
        collection = self.get_or_create(book)
        collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=[emb.tolist() for emb in embeddings],
            metadatas=[c.metadata for c in chunks],
        )

    def query(
        self,
        book: str,
        query_embedding: NDArray,
        top_k: int | None = None,
    ) -> list[dict]:
        collection = self.get_or_create(book)
        k = top_k or SETTINGS.top_k
        res = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k,
        )
        items: list[dict] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            items.append(
                {
                    "chunk_id": cid,
                    "text": doc,
                    "metadata": meta or {},
                    "score": 1.0 - float(dist) if dist is not None else 0.0,
                }
            )
        return items

    def file_hashes(self, book: str) -> dict[str, str]:
        collection = self.get_or_create(book)
        out: dict[str, str] = {}
        res = collection.get(include=["metadatas"])
        for cid, meta in zip(res.get("ids", []), res.get("metadatas", [])):
            if meta and "file_path" in meta and "content_hash" in meta:
                out[meta["file_path"]] = meta["content_hash"]
        return out
