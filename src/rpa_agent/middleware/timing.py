"""Logs each tool call with its duration."""

import logging
import time

import mcp_types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

logger = logging.getLogger(__name__)


class ToolTimingMiddleware(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        start = time.perf_counter()
        try:
            return await call_next(context)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("tool %s finished in %.1f ms", context.message.name, elapsed_ms)
