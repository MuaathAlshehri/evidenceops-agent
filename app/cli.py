import asyncio

from app.orchestrator import run_research


def display_result(result) -> None:
    print(f"\nReport ID: {result.report_id}")
    print(f"Status: {result.status.value}")

    if result.error:
        print(f"Error: {result.error}")
        return

    print("\n" + result.content)


async def main() -> None:
    print("EvidenceOps Agent - type 'exit' to stop")

    while True:
        question = input("\nResearch question: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        draft = await run_research(
            question=question,
            approved_to_save=False,
        )

        if draft.error:
            display_result(draft)
            continue

        print("\n--- Draft ---")
        display_result(draft)

        approval = input(
            "\nSave an approved final report? [y/N]: "
        ).strip().lower()

        if approval == "y":
            final_result = await run_research(
                question=question,
                approved_to_save=True,
            )

            print("\n--- Final Run ---")
            display_result(final_result)
        else:
            print("\nDraft was not saved.")


if __name__ == "__main__":
    asyncio.run(main())