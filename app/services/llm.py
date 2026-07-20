import os
import logging
from llama_index.core import Settings
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.config import config


logger = logging.getLogger(__name__)

_models_configured = False


def configure_models() -> None:
    global _models_configured

    if _models_configured:
        return

    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = (
        config.aws_bearer_token_bedrock
    )

    Settings.llm = BedrockConverse(
        model=config.model_name,
        region_name=config.aws_region,
        temperature=config.llm_temperature,
        max_tokens=3000,
    )

    Settings.embed_model = HuggingFaceEmbedding(
        model_name=config.embedding_model,
    )

    _models_configured = True

    logger.info("Provider: %s", config.model_provider)
    logger.info("LLM Model: %s", config.model_name)
    logger.info("AWS Region: %s", config.aws_region)
    logger.info("Embedding Model: %s", config.embedding_model)