from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_provider: str
    model_name: str
    aws_region: str
    aws_bearer_token_bedrock: str | None = None
    llm_temperature: float = 0.1
    embedding_model: str
    data_dir: str = "data/processed"
    storage_dir: str = "storage"
    top_k: int = 3
    model_config = SettingsConfigDict(env_file=".env")

    @model_validator(mode="after")
    def validate_credentials(self):
        provider = self.model_provider.lower().strip()

        if provider == "bedrock" and not self.aws_bearer_token_bedrock:
            raise ValueError(
                "Amazon Bedrock API key is missing. "
                "Add AWS_BEARER_TOKEN_BEDROCK to your .env file."
            )

        return self


config = Config()