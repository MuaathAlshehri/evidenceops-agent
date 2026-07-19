from pathlib import Path
from llama_index.core import StorageContext,load_index_from_storage
from app.config import config
from app.services.llm import configure_models
from functools import lru_cache

@lru_cache(maxsize=8)
def load_query_engine(experiment_name: str = "chunk_350_overlap_50",top_k: int | None = None):
    configure_models()

    storage_path = Path(config.storage_dir) / experiment_name

    if not storage_path.exists():
        raise FileNotFoundError(
            f"Storage directory not found: {storage_path}"
        )

    storage_context = StorageContext.from_defaults(
        persist_dir=str(storage_path)
    )

    index = load_index_from_storage(storage_context)

    return index.as_query_engine(
        top_k=top_k or config.top_k
    )

def load_query_engine(experiment_name: str = "chunk_350_overlap_50" ,top_k: int | None = None):
    configure_models()
    storage_path = (Path(config.storage_dir)/ experiment_name)

    if not storage_path.exists():
        raise FileNotFoundError(f"Storage directory not found: {storage_path}")

    storage_context = StorageContext.from_defaults(persist_dir=str(storage_path))

    index = load_index_from_storage(storage_context)

    return index.as_query_engine(similarity_top_k=top_k or config.top_k)