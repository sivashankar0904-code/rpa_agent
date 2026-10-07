"""Structured outputs for application tools."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InstalledApp(BaseModel):
    name: str
    version: str | None
    publisher: str | None
    # "store" and "desktop" come from the Start menu; "registry" apps have no Start entry.
    source: Literal["store", "desktop", "registry"]
    # Start-menu AppID (Store: `<Package>_<publisherId>!<App>`, desktop: path or app id).
    app_id: str | None
    # True if open_application can launch *and* track it. Other Start entries (browsers that use
    # an app id, shortcut-based entries, documents) are listed but not launchable.
    launchable: bool


class AppStatus(BaseModel):
    app_id: str
    name: str
    pid: int
    state: Literal["running", "exited"]
    exit_code: int | None
    started_at: datetime
