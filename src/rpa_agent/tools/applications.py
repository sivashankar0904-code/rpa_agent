"""Application lifecycle tools: open, monitor, terminate."""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from rpa_agent.core.errors import RpaAgentError
from rpa_agent.schemas.applications import AppStatus, InstalledApp
from rpa_agent.services.application_service import ApplicationService

_EXPECTED_ERRORS = (RpaAgentError, OSError)


def create_applications_server(service: ApplicationService) -> FastMCP:
    server = FastMCP("applications", mask_error_details=True)

    @server.tool
    def open_application(name: str, args: list[str] | None = None) -> AppStatus:
        """Launch an installed application by name and return its app_id and status.

        `name` is matched against list_installed_applications (exact, else unique substring).
        Only entries with launchable=true can be opened; blocked apps are refused.
        """
        try:
            return service.open(name, args)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    @server.tool(annotations={"readOnlyHint": True})
    def list_installed_applications(query: str | None = None) -> list[InstalledApp]:
        """List applications installed on this machine (Windows), optionally filtered by name.

        Each entry says whether open_application can launch it (`launchable`).
        """
        try:
            return service.list_installed(query)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    @server.tool(annotations={"readOnlyHint": True})
    def get_application_status(app_id: str) -> AppStatus:
        """Report whether an application launched by this server is running or has exited."""
        try:
            return service.status(app_id)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    @server.tool(annotations={"readOnlyHint": True})
    def list_applications() -> list[AppStatus]:
        """List every application launched by this server, with current status."""
        return service.list_apps()

    @server.tool(annotations={"destructiveHint": True})
    def terminate_application(app_id: str, timeout_seconds: float = 5.0) -> AppStatus:
        """Terminate an application, force-killing it if it ignores the request for the timeout."""
        try:
            return service.terminate(app_id, timeout_seconds)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    return server
