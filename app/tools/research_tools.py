from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, TypeVar

from llama_index.core import Settings
from llama_index.core.tools import FunctionTool

from app.services.index_service import load_query_engine


DEFAULT_EXPERIMENT = "chunk_350_overlap_50"
MAX_TOPIC_LENGTH = 200

T = TypeVar("T")


def measure_time(
    task_name: str,
    function: Callable[[], T],
) -> T:
    start_time = perf_counter()

    try:
        return function()
    finally:
        elapsed_time = perf_counter() - start_time
        print(
            f"[TIME] {task_name}: "
            f"{elapsed_time:.2f} seconds"
        )


def track_tool(
    tools_used: list[str],
    tool_name: str,
) -> None:
    tools_used.append(tool_name)


def save_report(
    title: str,
    content: str,
) -> str:
    title = title.strip()
    content = content.strip()

    if not title:
        raise ValueError("Report title cannot be empty.")

    if not content:
        raise ValueError("Report content cannot be empty.")

    reports_dir = Path("reports")
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = "".join(
        character
        for character in title.lower().replace(" ", "_")
        if character.isalnum() or character == "_"
    )

    file_name = safe_name[:60] or "report"
    path = reports_dir / f"{file_name}.md"

    if path.exists():
        raise FileExistsError(
            f"A report with this title already exists: {path}"
        )

    measure_time(
        "save_report: write file",
        lambda: path.write_text(
            content,
            encoding="utf-8",
        ),
    )

    return json.dumps(
        {
            "status": "saved",
            "path": str(path),
        },
        ensure_ascii=False,
    )


def record_audit_event(
    action: str,
    detail: str,
) -> str:
    action = action.strip()
    detail = detail.strip()

    if not action:
        raise ValueError("Audit action cannot be empty.")

    if not detail:
        raise ValueError("Audit detail cannot be empty.")

    log_path = Path("reports/audit_log.jsonl")
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    event = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "action": action,
        "detail": detail,
    }

    def write_audit_event() -> None:
        with log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    event,
                    ensure_ascii=False,
                )
                + "\n"
            )

    measure_time(
        "record_audit_event: write file",
        write_audit_event,
    )

    return json.dumps(
        {
            "status": "recorded",
            "event": event,
        },
        ensure_ascii=False,
    )


def validate_topics(
    topic_one: str,
    topic_two: str,
) -> tuple[str, str]:
    topic_one = topic_one.strip()
    topic_two = topic_two.strip()

    if not topic_one or not topic_two:
        raise ValueError("Both topics are required.")

    if len(topic_one) > MAX_TOPIC_LENGTH:
        raise ValueError(
            f"Topic one must be "
            f"{MAX_TOPIC_LENGTH} characters or fewer."
        )

    if len(topic_two) > MAX_TOPIC_LENGTH:
        raise ValueError(
            f"Topic two must be "
            f"{MAX_TOPIC_LENGTH} characters or fewer."
        )

    if topic_one.casefold() == topic_two.casefold():
        raise ValueError(
            "The two topics must be different."
        )

    return topic_one, topic_two


def compare_sources(
    topic_one: str,
    topic_two: str,
) -> str:
    topic_one, topic_two = validate_topics(
        topic_one,
        topic_two,
    )

    query_engine = measure_time(
        "compare_sources: load query engine",
        lambda: load_query_engine(
            experiment_name=DEFAULT_EXPERIMENT,
        ),
    )

    analysis_template = """
Using only the indexed knowledge base, analyze this topic:

Topic: {topic}

Return exactly:
1. Main Purpose
2. Main Concepts
3. Controls or Practices
4. Risks
5. Evidence Limitations

Do not introduce unsupported external information.
"""

    first_response = measure_time(
        f"compare_sources: analyze {topic_one}",
        lambda: query_engine.query(
            analysis_template.format(
                topic=topic_one
            )
        ),
    )

    second_response = measure_time(
        f"compare_sources: analyze {topic_two}",
        lambda: query_engine.query(
            analysis_template.format(
                topic=topic_two
            )
        ),
    )

    comparison_prompt = f"""
Compare the following two evidence summaries.

Topic One: {topic_one}
Topic One Findings:
{first_response}

Topic Two: {topic_two}
Topic Two Findings:
{second_response}

Return exactly:
1. Overlap
2. Differences
3. Evidence Limitations
4. Conclusion

Use only the supplied findings.
Clearly distinguish evidence from inference.
Do not introduce external information.
"""

    comparison_response = measure_time(
        "compare_sources: final LLM comparison",
        lambda: Settings.llm.complete(
            comparison_prompt
        ),
    )

    result = {
        "topics": {
            "topic_one": topic_one,
            "topic_two": topic_two,
        },
        "topic_one_findings": str(
            first_response
        ),
        "topic_two_findings": str(
            second_response
        ),
        "comparison": str(
            comparison_response
        ),
    }

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


def build_tools(
    approved_to_save: bool = False,
    tools_used: list[str] | None = None,
):
    if tools_used is None:
        tools_used = []

    query_engine = measure_time(
        "build_tools: load query engine",
        lambda: load_query_engine(
            experiment_name=DEFAULT_EXPERIMENT,
        ),
    )

    def knowledge_base_search(
        query: str,
    ) -> str:
        track_tool(
            tools_used,
            "knowledge_base_search",
        )

        response = measure_time(
            "knowledge_base_search: query",
            lambda: query_engine.query(
                query
            ),
        )

        return str(response)

    def tracked_compare_sources(
        topic_one: str,
        topic_two: str,
    ) -> str:
        track_tool(
            tools_used,
            "compare_sources",
        )

        return measure_time(
            "compare_sources: total",
            lambda: compare_sources(
                topic_one=topic_one,
                topic_two=topic_two,
            ),
        )

    def tracked_record_audit_event(
        action: str,
        detail: str,
    ) -> str:
        track_tool(
            tools_used,
            "record_audit_event",
        )

        return measure_time(
            "record_audit_event: total",
            lambda: record_audit_event(
                action=action,
                detail=detail,
            ),
        )

    def tracked_save_report(
        title: str,
        content: str,
    ) -> str:
        track_tool(
            tools_used,
            "save_report",
        )

        return measure_time(
            "save_report: total",
            lambda: save_report(
                title=title,
                content=content,
            ),
        )

    knowledge_tool = FunctionTool.from_defaults(
        fn=knowledge_base_search,
        name="knowledge_base_search",
        description=(
            "Search the indexed AI governance and security "
            "knowledge base for factual, source-grounded "
            "information. Use this tool for questions about "
            "AI governance, risks, controls, standards, "
            "compliance, incident response, or agent security."
        ),
    )

    compare_tool = FunctionTool.from_defaults(
        fn=tracked_compare_sources,
        name="compare_sources",
        description=(
            "Compare two distinct AI governance, risk, "
            "security, or compliance topics using the "
            "indexed knowledge base. Use this only when "
            "the user explicitly requests a comparison. "
            "Returns findings, overlap, differences, and "
            "evidence limitations. This tool does not "
            "write files."
        ),
    )

    audit_tool = FunctionTool.from_defaults(
        fn=tracked_record_audit_event,
        name="record_audit_event",
        description=(
            "Record a concise audit event after an important "
            "or consequential agent action, such as saving "
            "a report."
        ),
    )

    tools = [
        knowledge_tool,
        compare_tool,
        audit_tool,
    ]

    if approved_to_save:
        save_tool = FunctionTool.from_defaults(
            fn=tracked_save_report,
            name="save_report",
            description=(
                "Save approved Markdown content to the local "
                "reports directory. Use only after explicit "
                "approval to create a file."
            ),
        )

        tools.append(save_tool)

    return tools