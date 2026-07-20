from __future__ import annotations

import asyncio
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
MAX_SEARCH_CALLS = 4
MAX_COMPARE_CALLS = 1
MAX_PARALLEL_TOPICS = 4

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

    return str(path)


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


def validate_parallel_topics(
    topics: list[str],
) -> list[str]:
    if not topics:
        raise ValueError(
            "At least one search topic is required."
        )

    if len(topics) > MAX_PARALLEL_TOPICS:
        raise ValueError(
            "A maximum of "
            f"{MAX_PARALLEL_TOPICS} parallel topics is allowed."
        )

    cleaned_topics: list[str] = []
    seen_topics: set[str] = set()

    for topic in topics:
        cleaned_topic = topic.strip()

        if not cleaned_topic:
            raise ValueError(
                "Parallel search topics cannot be empty."
            )

        if len(cleaned_topic) > MAX_TOPIC_LENGTH:
            raise ValueError(
                "Each parallel search topic must be "
                f"{MAX_TOPIC_LENGTH} characters or fewer."
            )

        normalized_topic = cleaned_topic.casefold()

        if normalized_topic in seen_topics:
            continue

        seen_topics.add(normalized_topic)
        cleaned_topics.append(cleaned_topic)

    if not cleaned_topics:
        raise ValueError(
            "No unique search topics were provided."
        )

    return cleaned_topics


async def parallel_knowledge_search(
    topics: list[str],
) -> dict[str, str]:
    """Search multiple independent topics concurrently.

    The query engine is loaded once, then each synchronous query is
    delegated to a worker thread so the searches can run in parallel.
    A failure for one topic is returned as an evidence limitation for that
    topic instead of cancelling all remaining searches.
    """
    cleaned_topics = validate_parallel_topics(
        topics
    )

    total_start = perf_counter()

    query_engine = measure_time(
        "parallel_knowledge_search: load query engine",
        lambda: load_query_engine(
            experiment_name=DEFAULT_EXPERIMENT,
        ),
    )

    async def search_topic(
        topic: str,
        search_number: int,
    ) -> tuple[str, str]:
        start_time = perf_counter()

        try:
            response = await asyncio.to_thread(
                query_engine.query,
                topic,
            )
            result = str(response)
        except Exception as exc:
            result = (
                "Evidence retrieval failed for this topic. "
                f"Error: {type(exc).__name__}: {exc}"
            )
        finally:
            elapsed_time = perf_counter() - start_time
            print(
                "[TIME] parallel_knowledge_search: query "
                f"[{search_number}/{len(cleaned_topics)}]: "
                f"{elapsed_time:.2f} seconds"
            )

        return topic, result

    results = await asyncio.gather(
        *(
            search_topic(
                topic=topic,
                search_number=index,
            )
            for index, topic in enumerate(
                cleaned_topics,
                start=1,
            )
        )
    )

    elapsed_total = perf_counter() - total_start
    print(
        "[TIME] parallel_knowledge_search: total "
        f"[{len(cleaned_topics)} topics]: "
        f"{elapsed_total:.2f} seconds"
    )

    return dict(results)


def build_tools(
    approved_to_save: bool = False,
    tools_used: list[str] | None = None,
) -> list[FunctionTool]:
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
        search_count = tools_used.count(
            "knowledge_base_search"
        )

        if search_count >= MAX_SEARCH_CALLS:
            return (
                "Knowledge base search limit reached. "
                "Do not call this tool again. "
                "Use the evidence already retrieved and produce "
                "the final response. Clearly state any remaining "
                "evidence limitations."
            )

        track_tool(
            tools_used,
            "knowledge_base_search",
        )

        current_search_number = search_count + 1

        response = measure_time(
            (
                "knowledge_base_search: query "
                f"[{current_search_number}/{MAX_SEARCH_CALLS}]"
            ),
            lambda: query_engine.query(
                query.strip()
            ),
        )

        return str(response)

    def tracked_compare_sources(
        topic_one: str,
        topic_two: str,
    ) -> str:
        compare_count = tools_used.count(
            "compare_sources"
        )

        if compare_count >= MAX_COMPARE_CALLS:
            return (
                "Source comparison limit reached. "
                "Do not call this tool again. "
                "Use the existing search and comparison evidence "
                "to produce the final response."
            )

        track_tool(
            tools_used,
            "compare_sources",
        )

        current_compare_number = compare_count + 1

        return measure_time(
            (
                "compare_sources: total "
                f"[{current_compare_number}/{MAX_COMPARE_CALLS}]"
            ),
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
            "information. Use concise, non-overlapping queries. "
            "A maximum of four searches is permitted per research "
            "request. Do not repeat a search for the same topic. "
            "After sufficient evidence is retrieved, stop using "
            "tools and produce the response."
        ),
    )

    compare_tool = FunctionTool.from_defaults(
        fn=tracked_compare_sources,
        name="compare_sources",
        description=(
            "Compare exactly two distinct AI governance, risk, "
            "security, or compliance topics using the indexed "
            "knowledge base. This tool may be called at most once "
            "per research request. Do not use it repeatedly for "
            "pairwise comparisons. For more than two frameworks, "
            "retrieve evidence using knowledge_base_search and "
            "perform the final multi-framework synthesis directly "
            "in the response."
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
    ]

    # Kept for backward compatibility. In the corrected approval flow,
    # run_research should always build the agent with approved_to_save=False.
    # Saving the existing draft is handled directly by the orchestrator.
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