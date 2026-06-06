from __future__ import annotations

from openai import OpenAI

from .auth import get_zen_api_key
from .config import SETTINGS


class LLM:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or get_zen_api_key()
        self.base_url = base_url or SETTINGS.zen_base_url
        self.model = model or SETTINGS.llm_model
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        chosen_model = model or self.model
        chosen_temp = SETTINGS.temperature if temperature is None else temperature
        kwargs: dict = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": chosen_temp,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        resp = self._client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        return content.strip()
