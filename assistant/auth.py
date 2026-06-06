from __future__ import annotations

import json
import os
from pathlib import Path

_AUTH_FILE = Path.home() / ".local" / "share" / "opencode" / "auth.json"
_PROVIDER_KEYS = ("opencode", "zen", "opencode-zen")


def _from_opencode_auth_file() -> str | None:
    if not _AUTH_FILE.exists():
        return None
    try:
        data = json.loads(_AUTH_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for key in _PROVIDER_KEYS:
        entry = data.get(key)
        if isinstance(entry, dict):
            api_key = entry.get("key") or entry.get("apiKey")
            if api_key:
                return api_key
        elif isinstance(entry, str) and entry:
            return entry
    for value in data.values():
        if isinstance(value, dict):
            api_key = value.get("key") or value.get("apiKey")
            if api_key:
                return api_key
    return None


def get_zen_api_key() -> str:
    env_key = os.getenv("OPENCODE_API_KEY") or os.getenv("ZEN_API_KEY")
    if env_key:
        return env_key.strip()
    file_key = _from_opencode_auth_file()
    if file_key:
        return file_key.strip()
    raise RuntimeError(
        "Could not find an OpenCode Zen API key. "
        "Set OPENCODE_API_KEY in your environment or .env, "
        f"or ensure {_AUTH_FILE} exists with valid credentials."
    )
