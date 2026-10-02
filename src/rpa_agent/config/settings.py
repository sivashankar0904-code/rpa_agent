from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RPA_", extra="ignore")

    anthropic_api_key: str = ""
    model: str = "claude-sonnet-5-5"
    max_steps: int = 20
    system_prompt_path: str = "prompts/system.md"


def get_settings() -> Settings:
    return Settings()
