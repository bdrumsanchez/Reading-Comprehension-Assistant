from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BOOKS_DIR = DATA_DIR / "books"
CACHE_DIR = DATA_DIR / "cache"
CHROMA_DIR = CACHE_DIR / "chroma"
EMBED_CACHE_DIR = CACHE_DIR / "embeddings"
SUMMARY_CACHE_DIR = CACHE_DIR / "summaries"
HISTORY_FILE = CACHE_DIR / ".repl_history"

CHROMA_DIR.mkdir(parents=True, exist_ok=True)
EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    zen_base_url: str = "https://opencode.ai/zen/v1"
    llm_model: str = os.getenv("RCA_LLM_MODEL", "deepseek-v4-flash-free")
    embed_model: str = os.getenv("RCA_EMBED_MODEL", "all-MiniLM-L6-v2")
    chunk_tokens: int = int(os.getenv("RCA_CHUNK_TOKENS", "800"))
    chunk_overlap: int = int(os.getenv("RCA_CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("RCA_TOP_K", "5"))
    temperature: float = float(os.getenv("RCA_TEMPERATURE", "0.3"))
    max_context_tokens: int = int(os.getenv("RCA_MAX_CONTEXT_TOKENS", "6000"))


SETTINGS = Settings()
