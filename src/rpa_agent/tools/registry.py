from rpa_agent.tools.base import Tool
from rpa_agent.tools.file_tools import ReadFile, WriteFile


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None):
        self._tools = {t.name: t for t in (tools or [ReadFile(), WriteFile()])}

    def specs(self) -> list[dict]:
        return [t.spec() for t in self._tools.values()]

    def call(self, name: str, args: dict) -> str:
        if name not in self._tools:
            return f"error: unknown tool {name}"
        try:
            return self._tools[name].run(**args)
        except Exception as e:  # surface tool errors to the model
            return f"error: {e}"
