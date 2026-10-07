"""Domain exceptions raised by services and translated to MCP errors by tools."""


class RpaAgentError(Exception):
    """Base class for all application errors."""


class WorkspaceAccessError(RpaAgentError):
    """A path resolves outside the configured workspace."""


class FileTooLargeError(RpaAgentError):
    """A file exceeds the configured size limit."""
