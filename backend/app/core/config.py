from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Afromind Intelligence"
    database_url: str = "sqlite:///./luna_ai.db"
    cors_origins: str = "http://localhost:3000"
    ai_provider: str = "openai_compatible"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
