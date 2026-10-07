"""File tools, sandboxed to the configured workspace."""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from rpa_agent.core.errors import RpaAgentError
from rpa_agent.schemas.files import FileInfo, WriteResult
from rpa_agent.services.file_service import FileService

_EXPECTED_ERRORS = (RpaAgentError, OSError)


def create_files_server(service: FileService) -> FastMCP:
    server = FastMCP("files", mask_error_details=True)

    @server.tool(annotations={"readOnlyHint": True})
    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the workspace."""
        try:
            return service.read_text(path)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    @server.tool
    def write_file(path: str, content: str) -> WriteResult:
        """Write UTF-8 text to a file in the workspace, creating parent directories."""
        try:
            return service.write_text(path, content)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    @server.tool(annotations={"readOnlyHint": True})
    def list_dir(path: str = ".") -> list[FileInfo]:
        """List entries in a workspace directory."""
        try:
            return service.list_dir(path)
        except _EXPECTED_ERRORS as e:
            raise ToolError(str(e)) from e

    return server
