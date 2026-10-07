"""Domain exceptions raised by services and translated to MCP errors by tools."""


class RpaAgentError(Exception):
    """Base class for all application errors."""


class WorkspaceAccessError(RpaAgentError):
    """A path resolves outside the configured workspace."""


class FileTooLargeError(RpaAgentError):
    """A file exceeds the configured size limit."""


class ApplicationNotAllowedError(RpaAgentError):
    """The requested application name is not in the configured allowlist."""


class ApplicationLaunchError(RpaAgentError):
    """The application started but its process could not be identified for tracking."""


class ApplicationNotFoundError(RpaAgentError):
    """No application with the given id was launched by this server."""
