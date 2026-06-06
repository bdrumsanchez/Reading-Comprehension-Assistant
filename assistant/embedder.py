from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EMBED_CACHE_DIR, SETTINGS


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or SETTINGS.embed_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _cache_path(self, digest: str) -> Path:
        return EMBED_CACHE_DIR / f"{digest}.npy"

    def embed_cached(self, texts: Sequence[str]) -> np.ndarray:
        results: list[np.ndarray | None] = [None] * len(texts)
        missing: list[tuple[int, str]] = []

        for i, t in enumerate(texts):
            digest = self._hash(t)
            path = self._cache_path(digest)
            if path.exists():
                results[i] = np.load(path)
            else:
                missing.append((i, t))

        if missing:
            to_encode = [t for _, t in missing]
            vectors = self.model.encode(
                to_encode,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for (i, t), v in zip(missing, vectors):
                digest = self._hash(t)
                np.save(self._cache_path(digest), v)
                results[i] = v

        return np.vstack(results).astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        v = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return v.astype(np.float32)
