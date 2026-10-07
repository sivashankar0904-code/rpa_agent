"""Reusable prompt templates."""

from fastmcp import FastMCP


def create_prompts_server() -> FastMCP:
    server = FastMCP("prompts", mask_error_details=True)

    @server.prompt
    def summarize_file(path: str, max_words: int = 150) -> str:
        """Ask the model to summarize a workspace file."""
        return (
            f"Use the read_file tool to read `{path}` from the workspace, then summarize it "
            f"in at most {max_words} words. Highlight action items, if any."
        )

    return server
