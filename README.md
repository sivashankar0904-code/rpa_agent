# rpa-agent

A [FastMCP](https://gofastmcp.com) server that exposes RPA-style automation tools over the Model Context Protocol.

## Layout

```
src/rpa_agent/
├── server.py        # create_server() factory: mounts sub-servers, middleware, /health
├── __main__.py      # CLI entry point (rpa-agent / python -m rpa_agent)
├── core/            # settings (RPA_* env vars), logging, domain errors
├── services/        # business logic with no MCP imports (unit-testable)
├── models/          # SQLAlchemy ORM models
├── schemas/         # pydantic models for structured tool output
├── tools/           # one FastMCP sub-server per domain (e.g. files.py)
├── resources/       # MCP resources (config://server)
├── prompts/         # MCP prompt templates
└── middleware/      # custom FastMCP middleware
tests/
├── unit/            # service-level tests
└── integration/     # in-memory fastmcp.Client tests against the full server
```

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env
```

> **Windows + WSL:** don't share `.venv` between the two. Each OS rewrites it in its own format.
> In WSL, run `export UV_PROJECT_ENVIRONMENT=.venv-wsl` (for example in `~/.bashrc`) first.

## Run

```sh
uv run rpa-agent                                  # stdio (default)
RPA_TRANSPORT=http uv run rpa-agent               # streamable HTTP on :8000, GET /health
uv run fastmcp dev inspector                      # MCP Inspector (reads fastmcp.json)
uv run fastmcp list src/rpa_agent/server.py       # list tools from the CLI
docker build -t rpa-agent . && docker run -p 8000:8000 rpa-agent
```

### Connect from Claude Code / Claude Desktop

```json
{
  "mcpServers": {
    "rpa-agent": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/rpa_agent", "run", "rpa-agent"]
    }
  }
}
```

## Tools

| Tool | Purpose |
| --- | --- |
| `read_file`, `write_file`, `list_dir` | Sandboxed workspace file access |
| `list_installed_applications(query?)` | Apps installed on this Windows machine, with a `launchable` flag; optional name filter |
| `open_application(name, args?)` | Launch an installed app by name; returns an `app_id` |
| `get_application_status(app_id)` | `running` / `exited` with exit code |
| `list_applications()` | All apps launched by this server |
| `terminate_application(app_id, timeout_seconds?)` | Graceful terminate, then force-kill after the timeout |

`open_application` accepts any installed app with `launchable: true` except those on the blocklist
(`RPA_BLOCKED_APPS`; by default shells, script hosts, `regedit`, `msiexec` and terminals). There is
no allowlist, so a connected client can start anything not blocked, and `args` are passed through
unchecked. Only run this server for clients you trust.

`name` is matched against the installed list: an exact name, otherwise a unique substring.

Launchable apps are Microsoft Store apps and Start-menu apps that point at a real `.exe`. Other
Start-menu entries (Chrome, Brave, LibreOffice, shortcut-based entries) are listed but not
launchable, because their process can't be reliably tracked and terminated. Store apps can't take
`args`. Apps that hand off to another process and exit (some launchers and updaters) show as
`exited` while the real window stays open.

Only apps started by this server can be monitored or terminated. Terminating stops the app's whole
process tree (graceful first, then force-kill), so unsaved work is lost.

## Development

```sh
uv run pytest
uv run ruff check . && uv run ruff format .
uv run mypy src
uv run pre-commit install
```

### Adding a tool

1. Put the logic in `services/<domain>_service.py`, and raise `RpaAgentError` subclasses for expected failures.
2. Put the input and output models in `schemas/<domain>.py`.
3. Add a `create_<domain>_server(...)` factory to `tools/<domain>.py`. It should register `@server.tool` functions that map domain errors to `ToolError`.
4. Mount it in `server.py`: `mcp.mount(create_<domain>_server(...))`.
5. Add unit tests for the service and an integration test through `Client`.
