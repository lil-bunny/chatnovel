from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            "../.env.example",
            ".env.example",
            "../.env",
            ".env",
        ),
        extra="ignore",
        env_ignore_empty=True,
    )

    llm_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    @property
    def api_key(self) -> str:
        return (self.llm_api_key or self.openai_api_key).strip()

    @property
    def model(self) -> str:
        return (self.openai_model or self.llm_model).strip() or "gpt-4o-mini"


settings = Settings()
