from pathlib import Path

from rpa_agent.tools.base import Tool


class ReadFile(Tool):
    name = "read_file"
    description = "Read a UTF-8 text file and return its contents."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def run(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")


class WriteFile(Tool):
    name = "write_file"
    description = "Write text to a file, creating parent directories if needed."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }

    def run(self, path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {path}"
