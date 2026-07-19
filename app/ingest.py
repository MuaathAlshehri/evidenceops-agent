from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from app.config import config
from app.services.llm import configure_models


def build_index(chunk_size: int,chunk_overlap: int) -> None:
    configure_models()

    data_path = Path(config.data_dir)

    storage_path = (Path(config.storage_dir)/ f"chunk_{chunk_size}_overlap_{chunk_overlap}")

    storage_path.mkdir(parents=True,exist_ok=True,)

    documents = SimpleDirectoryReader(input_dir=str(data_path),recursive=True,required_exts=[".txt"],).load_data()

    if not documents:
        raise RuntimeError(f"No documents found in: {data_path}")

    for document in documents:
        file_name = document.metadata.get("file_name","unknown",)

        document.metadata["source_type"] = (Path(file_name).suffix.lower())

        document.metadata["collection"] = ("evidenceops_knowledge")

        document.metadata["chunk_size"] = chunk_size
        document.metadata["chunk_overlap"] = chunk_overlap

    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    nodes = splitter.get_nodes_from_documents(documents)

    if not nodes:
        raise RuntimeError("Documents were loaded, but no nodes were created.")

    index = VectorStoreIndex(nodes,show_progress=True,)

    index.storage_context.persist(persist_dir=str(storage_path))

    print("\nIndex created successfully")
    print(f"Documents: {len(documents)}")
    print(f"Nodes: {len(nodes)}")
    print(f"Chunk size: {chunk_size}")
    print(f"Chunk overlap: {chunk_overlap}")
    print(f"Storage: {storage_path.resolve()}")


def build_experiments() -> None:
    experiments = [
        (350, 50),
        (700, 100),
        (1200, 150),
    ]

    for chunk_size, chunk_overlap in experiments:
        print("\n" + "=" * 70)
        print(
            f"Building experiment: "
            f"chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}"
        )
        print("=" * 70)

        build_index(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


if __name__ == "__main__":
    build_experiments()