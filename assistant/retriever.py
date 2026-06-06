from __future__ import annotations

from .embedder import Embedder
from .store import VectorStore


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    def retrieve(self, book: str, query: str, top_k: int | None = None) -> list[dict]:
        q_vec = self.embedder.embed_query(query)
        return self.store.query(book=book, query_embedding=q_vec, top_k=top_k)
