import os

import anthropic

from rpa_agent.config.settings import Settings


class LLMClient:
    """Thin wrapper over the Anthropic Messages API."""

    def __init__(self, settings: Settings):
        self._model = settings.model
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, system: str, messages: list[dict], tools: list[dict]):
        return self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        )
