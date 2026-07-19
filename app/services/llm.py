from llama_index.core import Settings 
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.config import config
import logging 

logger = logging.getLogger(__name__)


_models_configured = False

def configure_models() -> None:

    global _models_configured

    if _models_configured:
        return
    
    Settings.llm = OpenAILike(
        model = config.model_name,
        api_key=config.api_key,
        api_base="https://openrouter.ai/api/v1",
        temperature = config.llm_temperature,
        is_chat_model=True,
        is_function_calling_model=True,
    )

    Settings.embed_model = HuggingFaceEmbedding(
        model_name = config.embedding_model
    )

    _models_configured = True
    
    logger.info("Provider: %s", config.model_provider)
    logger.info("LLM Model: %s", config.model_name)
    logger.info("Embedding Model: %s", config.embedding_model)