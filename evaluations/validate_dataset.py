import json
from pathlib import Path


DATASET_PATH = Path("evaluations/evaluation_dataset.jsonl")

REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_source",
    "expected_tools",
    "prohibited_tools",
    "grading_notes",
    "approved_to_save",
}


def validate_record(record: dict, line_number: int) -> list[str]:
    errors = []

    missing_fields = REQUIRED_FIELDS - record.keys()

    if missing_fields:
        errors.append(
            f"Line {line_number}: missing fields: {sorted(missing_fields)}"
        )

    if not isinstance(record.get("id"), str):
        errors.append(f"Line {line_number}: id must be a string")

    if not isinstance(record.get("question"), str):
        errors.append(f"Line {line_number}: question must be a string")

    if record.get("expected_source") is not None and not isinstance(
        record.get("expected_source"),
        str,
    ):
        errors.append(
            f"Line {line_number}: expected_source must be a string or null"
        )

        expected_tools = record.get("expected_tools")

        if not isinstance(expected_tools, list):
            errors.append(
                f"Line {line_number}: expected_tools must be a list"
            )
        elif not all(
            isinstance(tool, str)
            for tool in expected_tools
        ):
            errors.append(
                f"Line {line_number}: every item in expected_tools must be a string"
            )

    if not isinstance(record.get("prohibited_tools"), list):
        errors.append(
            f"Line {line_number}: prohibited_tools must be a list"
        )

    if not isinstance(record.get("grading_notes"), str):
        errors.append(
            f"Line {line_number}: grading_notes must be a string"
        )

    if not isinstance(record.get("approved_to_save"), bool):
        errors.append(
            f"Line {line_number}: approved_to_save must be a boolean"
        )

    return errors


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    all_errors = []
    record_ids = set()
    total_records = 0

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            total_records += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                all_errors.append(
                    f"Line {line_number}: invalid JSON: {error}"
                )
                continue

            all_errors.extend(
                validate_record(record, line_number)
            )

            record_id = record.get("id")

            if record_id in record_ids:
                all_errors.append(
                    f"Line {line_number}: duplicate id: {record_id}"
                )

            record_ids.add(record_id)

    if all_errors:
        print("Dataset validation failed:\n")

        for error in all_errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("Dataset validation passed")
    print(f"Total records: {total_records}")


if __name__ == "__main__":
    main()