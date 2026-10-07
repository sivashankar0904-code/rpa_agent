from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastmcp import Client

from rpa_agent.core.config import Settings
from rpa_agent.server import create_server
from rpa_agent.services.file_service import FileService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(workspace_dir=tmp_path / "workspace", max_file_bytes=1024)


@pytest.fixture
def file_service(settings: Settings) -> FileService:
    return FileService(settings.workspace_dir, settings.max_file_bytes)


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[Client]:
    """In-memory MCP client connected to a server with a temporary workspace."""
    async with Client(create_server(settings)) as c:
        yield c
