"""Application settings loaded from environment variables and `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rpa_agent.schemas.applications import AppSpec


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RPA_", extra="ignore")

    app_name: str = "rpa-agent"
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    workspace_dir: Path = Path("workspace")
    max_file_bytes: int = 1_000_000
    # Alias -> launch spec. Only these can be launched; set RPA_ALLOWED_APPS as a JSON object whose
    # values are either a command string or {"command": ..., "process_name": ...}.
    allowed_apps: dict[str, AppSpec] = {
        "notepad": AppSpec(command="notepad.exe", process_name="Notepad.exe"),
        "calc": AppSpec(command="calc.exe", process_name="CalculatorApp.exe"),
    }

    @field_validator("allowed_apps", mode="before")
    @classmethod
    def _bare_commands(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: {"command": v} if isinstance(v, str) else v for k, v in value.items()}
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
