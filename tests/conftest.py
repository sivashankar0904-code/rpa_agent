import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastmcp import Client

from rpa_agent.core.config import Settings
from rpa_agent.schemas.applications import AppSpec
from rpa_agent.server import create_server
from rpa_agent.services.application_service import ApplicationService
from rpa_agent.services.file_service import FileService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        workspace_dir=tmp_path / "workspace",
        max_file_bytes=1024,
        allowed_apps={"python": AppSpec(command=sys.executable)},
    )


@pytest.fixture
def file_service(settings: Settings) -> FileService:
    return FileService(settings.workspace_dir, settings.max_file_bytes)


@pytest.fixture
def application_service(settings: Settings) -> Iterator[ApplicationService]:
    service = ApplicationService(settings.allowed_apps)
    yield service
    # Never leak test processes, even when an assertion fails mid-test.
    for app in service.list_apps():
        if app.state == "running":
            service.terminate(app.app_id, timeout=1)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[Client]:
    """In-memory MCP client connected to a server with a temporary workspace."""
    async with Client(create_server(settings)) as c:
        yield c
