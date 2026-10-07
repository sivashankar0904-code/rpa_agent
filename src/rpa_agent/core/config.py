"""Application settings loaded from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shells, script hosts and system tools that let a client run arbitrary code or change the system.
DEFAULT_BLOCKED_APPS = [
    "cmd.exe",
    "powershell.exe",
    "powershell_ise.exe",
    "pwsh.exe",
    "wt.exe",
    "windowsterminal.exe",
    "Microsoft.WindowsTerminal",
    "wsl.exe",
    "bash.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
    "rundll32.exe",
    "regsvr32.exe",
    "regedit.exe",
    "msiexec.exe",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RPA_", extra="ignore")

    app_name: str = "rpa-agent"
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    workspace_dir: Path = Path("workspace")
    max_file_bytes: int = 1_000_000
    # Applications that open_application refuses to launch. Each entry is matched
    # case-insensitively against the app's display name, executable name (with or without
    # ".exe") and, for Store apps, package name. Set RPA_BLOCKED_APPS as a JSON list.
    blocked_apps: list[str] = DEFAULT_BLOCKED_APPS


@lru_cache
def get_settings() -> Settings:
    return Settings()
