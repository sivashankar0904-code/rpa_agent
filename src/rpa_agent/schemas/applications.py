"""Structured outputs for application tools."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AppSpec(BaseModel):
    """How to launch an allowlisted application.

    Some Windows apps (Notepad, Calculator) start through a launcher stub that exits immediately
    while the real window runs as a separate process. Set `process_name` to the real process's
    image name (e.g. "Notepad.exe") so it is tracked and terminated instead of the stub.
    """

    command: str
    process_name: str | None = None


class AppStatus(BaseModel):
    app_id: str
    name: str
    pid: int
    state: Literal["running", "exited"]
    exit_code: int | None
    started_at: datetime
