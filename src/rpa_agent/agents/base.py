from pathlib import Path

from rpa_agent.config.settings import Settings
from rpa_agent.llm.client import LLMClient
from rpa_agent.memory.short_term import ConversationMemory
from rpa_agent.tools.registry import ToolRegistry


class Agent:
    """Tool-use loop: call the model, run requested tools, feed results back."""

    def __init__(self, settings: Settings, tools: ToolRegistry | None = None):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.tools = tools or ToolRegistry()
        self.system = Path(settings.system_prompt_path).read_text(encoding="utf-8")

    def run(self, task: str) -> str:
        memory = ConversationMemory()
        memory.add("user", task)
        for _ in range(self.settings.max_steps):
            resp = self.llm.complete(self.system, memory.messages, self.tools.specs())
            memory.add("assistant", resp.content)
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            results = [
                {
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": self.tools.call(b.name, b.input),
                }
                for b in resp.content
                if b.type == "tool_use"
            ]
            memory.add("user", results)
        return "Stopped: max steps reached."
