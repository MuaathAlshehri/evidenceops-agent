from pathlib import Path

from app.tools.research_tools import (
    record_audit_event,
    save_report,
)


def test_save_report_creates_markdown_file(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    message = save_report(
        "Test Report",
        "# Result",
    )

    assert "saved" in message.lower()
    assert Path("reports/test_report.md").exists()


def test_record_audit_event_creates_jsonl(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    record_audit_event(
        "test",
        "tool executed",
    )

    assert Path("reports/audit_log.jsonl").exists()