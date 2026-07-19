from pydantic_settings import BaseSettings , SettingsConfigDict
from pydantic import model_validator

class Config(BaseSettings):
    model_provider: str
    model_name: str
    api_key: str | None = None
    llm_temperature: float
    embedding_model : str 
    data_dir: str = "data/processed"
    storage_dir: str = "storage"
    top_k: int = 3


    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode = "after")
    def validate_api_key(self):
        if self.model_provider.lower() == "openrouter" and not self.api_key:
            raise ValueError("OpenRouter API key is missing. Please add API_KEY to your .env file.")
        return self


config = Config()