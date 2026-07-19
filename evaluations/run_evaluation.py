import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.orchestrator import run_research


DATASET_PATH = Path("evaluations/evaluation_dataset.jsonl")
RESULTS_PATH = Path("evaluations/evaluation_results.jsonl")


def load_dataset() -> list[dict[str, Any]]:
    cases = []

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

            cases.append(case)

    return cases


def convert_result_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        return result.to_dict()

    if isinstance(result, dict):
        return result

    return {
        "raw_result": str(result),
    }


def build_result_record(
    case: dict[str, Any],
    latency_seconds: float,
    execution_error: str | None,
    agent_result: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": case["id"],
        "question": case["question"],
        "expected_source": case.get("expected_source"),
        "expected_tools": case.get("expected_tools", []),
        "prohibited_tools": case.get("prohibited_tools", []),
        "approved_to_save": case.get("approved_to_save", False),
        "grading_notes": case.get("grading_notes", ""),
        "latency_seconds": round(latency_seconds, 3),
        "execution_error": execution_error,
        "agent_result": agent_result,
    }


async def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    print(f"Running {case['id']}: {case['question']}")

    start_time = time.perf_counter()

    try:
        result = await run_research(
            question=case["question"],
            approved_to_save=case.get("approved_to_save", False),
        )

        latency_seconds = time.perf_counter() - start_time

        print(
            f"Completed {case['id']} "
            f"in {latency_seconds:.2f} seconds"
        )

        return build_result_record(
            case=case,
            latency_seconds=latency_seconds,
            execution_error=None,
            agent_result=convert_result_to_dict(result),
        )

    except Exception as error:
        latency_seconds = time.perf_counter() - start_time

        print(f"Failed {case['id']}: {error}")

        return build_result_record(
            case=case,
            latency_seconds=latency_seconds,
            execution_error=str(error),
            agent_result=None,
        )


async def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    cases = load_dataset()

    print(f"Loaded {len(cases)} evaluation cases.\n")

    results = []

    for case in cases:
        result = await evaluate_case(case)
        results.append(result)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(
                json.dumps(result, ensure_ascii=False) + "\n"
            )

    successful = sum(
        result["execution_error"] is None
        and result["agent_result"] is not None
        and result["agent_result"].get("status") != "failed"
        for result in results
    )

    agent_failures = sum(
        result["agent_result"] is not None
        and result["agent_result"].get("status") == "failed"
        for result in results
    )

    execution_failures = sum(
        result["execution_error"] is not None
        for result in results
    )

    total_failures = len(results) - successful

    print("\nEvaluation execution completed")
    print(f"Total cases: {len(results)}")
    print(f"Executed successfully: {successful}")
    print(f"Total failures: {total_failures}")
    print(f"Execution failures: {execution_failures}")
    print(f"Agent failures: {agent_failures}")
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())