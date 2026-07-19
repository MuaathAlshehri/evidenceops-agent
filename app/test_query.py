from app.services.index_service import load_query_engine


def main() -> None:
    engine = load_query_engine(
        experiment_name="chunk_1200_overlap_150"
    )

    question = (
        "What controls should govern "
        "consequential agent actions?"
    )

    response = engine.query(question)

    print("\nAnswer:")
    print(response)

    print("\nRetrieved source nodes:")

    for position, source_node in enumerate(
        response.source_nodes,
        start=1,
    ):
        node = source_node.node

        print("\n" + "=" * 80)
        print(f"Source {position}")
        print(f"Similarity score: {source_node.score}")
        print(f"Metadata: {node.metadata}")
        print("-" * 80)
        print(node.get_content())


if __name__ == "__main__":
    main()