import sys
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
from fastmcp import Client

from rpa_agent.core.config import Settings
from rpa_agent.schemas.applications import InstalledApp
from rpa_agent.server import create_server
from rpa_agent.services.application_service import ApplicationService
from rpa_agent.services.file_service import FileService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(workspace_dir=tmp_path / "workspace", max_file_bytes=1024)


@pytest.fixture
def file_service(settings: Settings) -> FileService:
    return FileService(settings.workspace_dir, settings.max_file_bytes)


def fake_app(name: str, app_id: str | None, launchable: bool = True) -> InstalledApp:
    return InstalledApp(
        name=name,
        version=None,
        publisher=None,
        source="desktop",
        app_id=app_id,
        launchable=launchable,
    )


@pytest.fixture
def installed() -> list[InstalledApp]:
    """A fake, machine-independent catalog; the "Test Python" apps are a real executable."""
    return [
        fake_app("Test Python", sys.executable),
        fake_app("Test Python Tools", sys.executable),
        fake_app("Shell Thing", sys.executable),
        fake_app("Docs Only", "https://example.com", launchable=False),
    ]


@pytest.fixture
def make_application_service(
    installed: list[InstalledApp],
) -> Iterator[Callable[[list[str]], ApplicationService]]:
    """Factory for services over the fake catalog; every launched app is cleaned up afterwards."""
    created: list[ApplicationService] = []

    def make(blocked: list[str]) -> ApplicationService:
        def catalog(query: str | None) -> list[InstalledApp]:
            needle = (query or "").lower()
            return [a for a in installed if needle in a.name.lower()]

        service = ApplicationService(blocked, catalog)
        created.append(service)
        return service

    yield make
    # Never leak test processes, even when an assertion fails mid-test.
    for service in created:
        for app in service.list_apps():
            if app.state == "running":
                service.terminate(app.app_id, timeout=1)


@pytest.fixture
def application_service(
    make_application_service: Callable[[list[str]], ApplicationService],
) -> ApplicationService:
    return make_application_service(["Shell Thing"])


@pytest.fixture
async def client(
    settings: Settings, application_service: ApplicationService
) -> AsyncIterator[Client]:
    """In-memory MCP client connected to a server with a temporary workspace."""
    async with Client(create_server(settings, application_service)) as c:
        yield c
