"""CLI entry point: `rpa-agent` or `python -m rpa_agent`."""

from rpa_agent.core.config import get_settings
from rpa_agent.server import mcp


def main() -> None:
    settings = get_settings()
    if settings.transport == "http":
        mcp.run(transport="http", host=settings.host, port=settings.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
