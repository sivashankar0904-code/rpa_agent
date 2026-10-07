"""Read-only resources describing the running server."""

import json

from fastmcp import FastMCP

from rpa_agent import __version__
from rpa_agent.core.config import Settings


def create_server_info_server(settings: Settings) -> FastMCP:
    server = FastMCP("server-info", mask_error_details=True)

    @server.resource("config://server", mime_type="application/json")
    def server_config() -> str:
        """Non-secret server configuration and version."""
        return json.dumps(
            {
                "name": settings.app_name,
                "version": __version__,
                "transport": settings.transport,
                "workspace_dir": str(settings.workspace_dir),
                "max_file_bytes": settings.max_file_bytes,
                "allowed_apps": sorted(settings.allowed_apps),
            }
        )

    return server
