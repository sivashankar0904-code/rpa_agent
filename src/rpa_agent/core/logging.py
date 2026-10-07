"""Logging setup. Always logs to stderr: stdout carries the MCP stdio protocol."""

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger("rpa_agent")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False
