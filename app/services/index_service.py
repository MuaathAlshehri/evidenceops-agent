from functools import lru_cache
from pathlib import Path
from time import perf_counter

from llama_index.core import (
    StorageContext,
    load_index_from_storage,
)

from app.config import config
from app.services.llm import configure_models


def print_time(task_name: str, start_time: float) -> None:
    elapsed_time = perf_counter() - start_time
    print(f"[TIME] {task_name}: {elapsed_time:.2f} seconds")


@lru_cache(maxsize=8)
def load_query_engine(
    experiment_name: str = "chunk_350_overlap_50",
    top_k: int | None = None,
):
    total_start = perf_counter()

    configure_start = perf_counter()
    configure_models()
    print_time(
        "index_service: configure models",
        configure_start,
    )

    storage_path = Path(config.storage_dir) / experiment_name

    if not storage_path.exists():
        raise FileNotFoundError(
            f"Storage directory not found: {storage_path}"
        )

    context_start = perf_counter()
    storage_context = StorageContext.from_defaults(
        persist_dir=str(storage_path)
    )
    print_time(
        "index_service: create storage context",
        context_start,
    )

    index_start = perf_counter()
    index = load_index_from_storage(storage_context)
    print_time(
        "index_service: load index from storage",
        index_start,
    )

    query_engine_start = perf_counter()
    query_engine = index.as_query_engine(
        similarity_top_k=(
            top_k
            if top_k is not None
            else config.top_k
        )
    )
    print_time(
        "index_service: create query engine",
        query_engine_start,
    )

    print_time(
        "index_service: total load query engine",
        total_start,
    )

    return query_engine