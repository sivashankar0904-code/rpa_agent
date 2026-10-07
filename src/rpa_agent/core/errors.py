"""Domain exceptions raised by services and translated to MCP errors by tools."""


class RpaAgentError(Exception):
    """Base class for all application errors."""


class WorkspaceAccessError(RpaAgentError):
    """A path resolves outside the configured workspace."""


class FileTooLargeError(RpaAgentError):
    """A file exceeds the configured size limit."""


class ApplicationBlockedError(RpaAgentError):
    """The application matches an entry in the configured blocklist."""


class ApplicationNotInstalledError(RpaAgentError):
    """No installed application matches the requested name, or the name is ambiguous."""


class ApplicationNotLaunchableError(RpaAgentError):
    """The application is installed but cannot be launched and tracked by this server."""


class CatalogUnavailableError(RpaAgentError):
    """The list of installed applications could not be read."""


class ApplicationLaunchError(RpaAgentError):
    """The application started but its process could not be identified for tracking."""


class UnsupportedPlatformError(RpaAgentError):
    """The operation is not available on this operating system."""


class ApplicationNotFoundError(RpaAgentError):
    """No application with the given id was launched by this server."""
