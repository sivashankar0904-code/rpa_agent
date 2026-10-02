class ConversationMemory:
    """Message history for a single agent run."""

    def __init__(self):
        self.messages: list[dict] = []

    def add(self, role: str, content) -> None:
        self.messages.append({"role": role, "content": content})
