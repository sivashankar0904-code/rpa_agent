"""Server factory: assembles domain sub-servers, middleware and HTTP routes."""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from rpa_agent import __version__
from rpa_agent.core.config import Settings, get_settings
from rpa_agent.core.logging import configure_logging
from rpa_agent.middleware.timing import ToolTimingMiddleware
from rpa_agent.prompts.templates import create_prompts_server
from rpa_agent.resources.server_info import create_server_info_server
from rpa_agent.services.file_service import FileService
from rpa_agent.tools.files import create_files_server

INSTRUCTIONS = """\
Tools for RPA-style automation. File tools operate inside a sandboxed workspace;
paths are relative to it. Read `config://server` for the current configuration.
"""


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    file_service = FileService(settings.workspace_dir, settings.max_file_bytes)

    # ToolError messages reach the client; other exceptions are masked to avoid leaking internals.
    mcp = FastMCP(
        settings.app_name,
        instructions=INSTRUCTIONS,
        version=__version__,
        middleware=[ToolTimingMiddleware()],
        mask_error_details=True,
    )
    mcp.mount(create_files_server(file_service))
    mcp.mount(create_server_info_server(settings))
    mcp.mount(create_prompts_server())

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    return mcp


mcp = create_server()
