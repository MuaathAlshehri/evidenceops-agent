from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from textwrap import dedent
from time import perf_counter
from uuid import uuid4

from llama_index.core import Settings

from app.agents.research_agent import build_agent
from app.tools.research_tools import (
    parallel_knowledge_search,
    save_report,
)


MIN_OBJECTIVE_LENGTH = 10
MAX_OBJECTIVE_LENGTH = 1500
MAX_EXECUTION_SECONDS = 180

AUDIT_LOG_PATH = Path("reports/audit_log.jsonl")

# Deterministic aliases used to route multi-framework comparisons to the
# faster parallel retrieval pipeline. Unknown or open-ended requests still
# fall back to the existing agent workflow.
FRAMEWORK_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "NIST AI Risk Management Framework",
        (
            "nist ai risk management framework",
            "nist ai rmf",
            "ai rmf",
        ),
    ),
    (
        "ISO/IEC 42001 AI Management System",
        (
            "iso/iec 42001",
            "iso 42001",
            "iso iec 42001",
        ),
    ),
    (
        "OWASP LLM Top 10",
        (
            "owasp llm top 10",
            "owasp top 10 for llm",
            "owasp llm",
        ),
    ),
    (
        "SDAIA AI Ethics Principles",
        (
            "sdaia ai ethics principles",
            "sdaia ethics principles",
            "sdaia ai ethics",
            "sdaia",
        ),
    ),
)

COMPARISON_MARKERS = (
    "compare",
    "comparison",
    "versus",
    " vs ",
    "قارن",
    "مقارنة",
    "بين",
)


IDENTITY_MARKERS = (
    "introduce yourself",
    "introduce your self",
    "introduce yourself to me",
    "tell me about yourself",
    "talk about yourself",
    "about yourself",
    "who are you",
    "what are you",
    "interduse about your self",
    "interduce yourself",
    "introduce yoursef",
    "عرف بنفسك",
    "عرّف بنفسك",
    "تكلم عن نفسك",
    "تحدث عن نفسك",
    "حدثني عن نفسك",
    "من أنت",
    "من انت",
)


class ResearchStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass
class ResearchResult:
    report_id: str
    objective: str
    status: ResearchStatus
    content: str
    approved_to_save: bool
    tools_used: list[str]
    unique_tools_used: list[str]
    saved_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        result = asdict(self)
        result["status"] = self.status.value
        return result


def print_time(
    task_name: str,
    start_time: float,
) -> None:
    elapsed_time = perf_counter() - start_time

    print(
        f"[TIME] {task_name}: "
        f"{elapsed_time:.2f} seconds"
    )


def validate_objective(question: str) -> str:
    if not isinstance(question, str):
        raise TypeError(
            "Research objective must be a string."
        )

    objective = question.strip()

    if not objective:
        raise ValueError(
            "Research objective cannot be empty."
        )

    if len(objective) < MIN_OBJECTIVE_LENGTH:
        raise ValueError(
            "Research objective is too short. "
            "Provide a specific research question."
        )

    if len(objective) > MAX_OBJECTIVE_LENGTH:
        raise ValueError(
            "Research objective cannot exceed "
            f"{MAX_OBJECTIVE_LENGTH} characters."
        )

    broad_objectives = {
        "tell me about ai",
        "research ai",
        "analyze ai",
        "research security",
        "research governance",
        "analyze everything",
        "compare everything",
        "tell me everything",
    }

    if objective.lower() in broad_objectives:
        raise ValueError(
            "Research objective is too broad. "
            "Specify a framework, risk, control, "
            "standard, or comparison."
        )

    return objective


def extract_parallel_topics(
    objective: str,
) -> list[str]:
    """
    Return recognized framework topics for deterministic parallel retrieval.

    The fast path is used only when the request is clearly comparative and at
    least two known frameworks are named. Other requests retain the flexible
    agent workflow.
    """
    normalized_objective = objective.casefold()

    if not any(
        marker in normalized_objective
        for marker in COMPARISON_MARKERS
    ):
        return []

    topics: list[str] = []

    for canonical_name, aliases in FRAMEWORK_ALIASES:
        if any(
            alias.casefold() in normalized_objective
            for alias in aliases
        ):
            topics.append(canonical_name)

    return topics if len(topics) >= 2 else []


def extract_single_topic(
    objective: str,
) -> str | None:
    """Return one recognized framework for the deterministic single-topic route."""
    normalized_objective = objective.casefold()

    if any(
        marker in normalized_objective
        for marker in COMPARISON_MARKERS
    ):
        return None

    matched_topics: list[str] = []

    for canonical_name, aliases in FRAMEWORK_ALIASES:
        if any(
            alias.casefold() in normalized_objective
            for alias in aliases
        ):
            matched_topics.append(canonical_name)

    if len(matched_topics) == 1:
        return matched_topics[0]

    return None


def is_identity_question(
    objective: str,
) -> bool:
    """Return True when the user is asking about the agent itself."""
    normalized_objective = " ".join(
        objective.casefold()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .split()
    )

    return any(
        " ".join(marker.casefold().split()) in normalized_objective
        for marker in IDENTITY_MARKERS
    )


def build_identity_response(
    report_id: str,
) -> str:
    """Answer identity questions without searching the knowledge base."""
    return dedent(
        f"""
        ## Findings

        I am EvidenceOps, an AI research operations agent focused on
        evidence-grounded research about AI governance, AI security,
        AI risk management, and AI compliance.

        I retrieve information from the indexed knowledge base, compare
        frameworks when requested, clearly identify evidence limitations,
        and produce a draft for review before any report is saved.

        ## Evidence Limitations

        This response describes the configured role of the agent and does
        not rely on external or indexed factual evidence.

        ## Confidence

        High confidence.

        ## Next Action

        This is a draft for research identifier {report_id}. Review the
        response and provide explicit approval before saving.
        """
    ).strip()


def record_orchestration_event(
    report_id: str,
    action: str,
    status: ResearchStatus,
    details: str | None = None,
) -> None:
    start_time = perf_counter()

    try:
        AUDIT_LOG_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        event = {
            "report_id": report_id,
            "action": action,
            "status": status.value,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if details:
            event["details"] = details

        with AUDIT_LOG_PATH.open(
            "a",
            encoding="utf-8",
        ) as audit_file:
            audit_file.write(
                json.dumps(
                    event,
                    ensure_ascii=False,
                )
                + "\n"
            )
    finally:
        print_time(
            f"orchestrator: audit event [{action}]",
            start_time,
        )


async def synthesize_parallel_comparison(
    report_id: str,
    objective: str,
    evidence: dict[str, str],
) -> str:
    """Create one grounded comparison from all retrieved evidence."""
    evidence_text = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
    )

    prompt = dedent(
        f"""
        Research identifier:
        {report_id}

        Research objective:
        {objective}

        Indexed knowledge base evidence:
        {evidence_text}

        Produce a draft research response using only the supplied evidence.
        Do not introduce external facts. Clearly label any interpretation or
        recommendation as inference. If the evidence for a requested framework
        or deliverable is incomplete, state that limitation explicitly rather
        than omitting the framework.

        Completion checklist:
        - Address every framework named in the research objective.
        - Explain objective, scope, key principles or controls, strengths,
          limitations, and typical use cases for each framework when supported.
        - Include a comparison matrix.
        - Identify overlaps and material differences.
        - Recommend an implementation roadmap.
        - Conclude with the best combination of frameworks.
        - Distinguish retrieved evidence from inference and recommendation.
        - State all evidence limitations.

        Use these response headings exactly once:
        ## Framework Analysis
        ## Comparison Matrix
        ## Overlaps
        ## Differences
        ## Implementation Roadmap
        ## Recommended Framework Combination
        ## Evidence Limitations
        ## Confidence
        ## Next Action

        In the Next Action section, state that this is a draft for research
        identifier {report_id} and request explicit approval before saving.
        """
    ).strip()

    synthesis_start = perf_counter()

    response = await asyncio.to_thread(
        Settings.llm.complete,
        prompt,
    )

    print_time(
        "orchestrator: parallel synthesis",
        synthesis_start,
    )

    return str(response)


async def synthesize_single_topic(
    report_id: str,
    objective: str,
    evidence: dict[str, str],
) -> str:
    """Create one grounded answer from a single knowledge-base retrieval."""
    evidence_text = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
    )

    prompt = dedent(
        f"""
        Research identifier:
        {report_id}

        Research objective:
        {objective}

        Indexed knowledge base evidence:
        {evidence_text}

        Produce a complete draft response using only the supplied evidence.
        Do not introduce external facts. Address every requested item in the
        objective. Clearly distinguish retrieved evidence from inference or
        recommendation. If the evidence is incomplete, state the limitation
        explicitly instead of performing another search.

        Use these response headings exactly once:
        ## Findings
        ## Evidence Limitations
        ## Confidence
        ## Next Action

        In the Next Action section, state that this is a draft for research
        identifier {report_id} and request explicit approval before saving.
        """
    ).strip()

    synthesis_start = perf_counter()

    response = await asyncio.to_thread(
        Settings.llm.complete,
        prompt,
    )

    print_time(
        "orchestrator: single-topic synthesis",
        synthesis_start,
    )

    return str(response)


async def run_research(
    question: str,
) -> ResearchResult:
    total_start = perf_counter()

    report_id = f"report-{uuid4().hex[:12]}"
    status = ResearchStatus.DRAFT
    tools_used: list[str] = []

    try:
        validation_start = perf_counter()
        objective = validate_objective(question)

        print_time(
            "orchestrator: validate objective",
            validation_start,
        )

        record_orchestration_event(
            report_id=report_id,
            action="research_started",
            status=status,
            details=objective,
        )

        parallel_topics = extract_parallel_topics(
            objective
        )
        single_topic = extract_single_topic(
            objective
        )
        identity_question = is_identity_question(
            objective
        )

        async with asyncio.timeout(
            MAX_EXECUTION_SECONDS
        ):
            if identity_question:
                route_start = perf_counter()

                record_orchestration_event(
                    report_id=report_id,
                    action="identity_route_selected",
                    status=status,
                )

                content = build_identity_response(
                    report_id=report_id,
                )

                print_time(
                    "orchestrator: identity route",
                    route_start,
                )

            elif parallel_topics:
                route_start = perf_counter()

                record_orchestration_event(
                    report_id=report_id,
                    action="parallel_research_route_selected",
                    status=status,
                    details=json.dumps(
                        parallel_topics,
                        ensure_ascii=False,
                    ),
                )

                evidence = await parallel_knowledge_search(
                    parallel_topics
                )

                tools_used.extend(
                    ["knowledge_base_search"]
                    * len(parallel_topics)
                )

                content = await synthesize_parallel_comparison(
                    report_id=report_id,
                    objective=objective,
                    evidence=evidence,
                )

                print_time(
                    "orchestrator: parallel research route",
                    route_start,
                )

            elif single_topic:
                route_start = perf_counter()

                record_orchestration_event(
                    report_id=report_id,
                    action="single_topic_route_selected",
                    status=status,
                    details=single_topic,
                )

                evidence = await parallel_knowledge_search(
                    [objective]
                )

                tools_used.append(
                    "knowledge_base_search"
                )

                content = await synthesize_single_topic(
                    report_id=report_id,
                    objective=objective,
                    evidence=evidence,
                )

                print_time(
                    "orchestrator: single-topic research route",
                    route_start,
                )

            else:
                build_agent_start = perf_counter()

                agent = build_agent(
                    approved_to_save=False,
                    tools_used=tools_used,
                )

                print_time(
                    "orchestrator: build agent",
                    build_agent_start,
                )

                approval_instruction = (
                    "The user has not approved saving. "
                    "The save_report tool is unavailable. "
                    "Return a draft response for review and request "
                    "explicit approval."
                )

                prompt_start = perf_counter()

                prompt = dedent(
                    f"""
                    Research identifier:
                    {report_id}

                    Research objective:
                    {objective}

                    Current status:
                    {status.value}

                    Approval constraint:
                    {approval_instruction}

                    Execution constraints:
                    - This approval applies only to research identifier {report_id}.
                    - Search the indexed knowledge base before factual claims.
                    - Use only the tools necessary to answer the objective.
                    - Do not claim that a report was saved unless the save_report
                      tool completed successfully.
                    - Include research identifier {report_id} in any audit event.
                    - Clearly distinguish retrieved evidence, inference, and
                      recommendation.
                    - State when indexed evidence is incomplete or unavailable.
                    - Before finishing, verify that every named framework and every
                      requested deliverable has been addressed.
                    - If evidence is missing, state the limitation explicitly rather
                      than omitting the requested item.

                    Use these response headings exactly once:
                    ## Findings
                    ## Evidence Limitations
                    ## Confidence
                    ## Next Action
                    """
                ).strip()

                print_time(
                    "orchestrator: build prompt",
                    prompt_start,
                )

                agent_run_start = perf_counter()

                result = await agent.run(
                    user_msg=prompt
                )

                print_time(
                    "orchestrator: agent run",
                    agent_run_start,
                )

                conversion_start = perf_counter()
                content = str(result)

                print_time(
                    "orchestrator: convert result to string",
                    conversion_start,
                )

        status = ResearchStatus.AWAITING_APPROVAL

        record_orchestration_event(
            report_id=report_id,
            action="draft_research_completed",
            status=status,
        )

        research_result = ResearchResult(
            report_id=report_id,
            objective=objective,
            status=status,
            content=content,
            approved_to_save=False,
            tools_used=tools_used,
            unique_tools_used=list(
                dict.fromkeys(tools_used)
            ),
        )

        print_time(
            "orchestrator: total research request",
            total_start,
        )

        return research_result

    except TimeoutError:
        status = ResearchStatus.FAILED

        error_message = (
            "Research execution exceeded "
            f"{MAX_EXECUTION_SECONDS} seconds."
        )

        record_orchestration_event(
            report_id=report_id,
            action="research_timeout",
            status=status,
            details=error_message,
        )

        print_time(
            "orchestrator: total request before timeout",
            total_start,
        )

        return ResearchResult(
            report_id=report_id,
            objective=(
                question.strip()
                if isinstance(question, str)
                else str(question)
            ),
            status=status,
            content="",
            approved_to_save=False,
            tools_used=tools_used,
            unique_tools_used=list(
                dict.fromkeys(tools_used)
            ),
            error=error_message,
        )

    except Exception as error:
        status = ResearchStatus.FAILED
        error_message = str(error)

        record_orchestration_event(
            report_id=report_id,
            action="research_failed",
            status=status,
            details=error_message,
        )

        print_time(
            "orchestrator: total request before failure",
            total_start,
        )

        return ResearchResult(
            report_id=report_id,
            objective=(
                question.strip()
                if isinstance(question, str)
                else str(question)
            ),
            status=status,
            content="",
            approved_to_save=False,
            tools_used=tools_used,
            unique_tools_used=list(
                dict.fromkeys(tools_used)
            ),
            error=error_message,
        )


async def approve_and_save(
    draft: ResearchResult,
) -> ResearchResult:
    """Save an existing draft without running research again."""
    start_time = perf_counter()

    try:
        if draft.error:
            raise ValueError(
                "A failed research result cannot be approved."
            )

        if draft.status != ResearchStatus.AWAITING_APPROVAL:
            raise ValueError(
                "Only a draft awaiting approval can be saved."
            )

        if not draft.content.strip():
            raise ValueError(
                "Draft content cannot be empty."
            )

        record_orchestration_event(
            report_id=draft.report_id,
            action="report_approval_received",
            status=ResearchStatus.AWAITING_APPROVAL,
        )

        title = (
            f"{draft.report_id}_"
            f"{draft.objective[:40]}"
        )

        save_start = perf_counter()

        saved_path = await asyncio.to_thread(
            save_report,
            title,
            draft.content,
        )

        print_time(
            "orchestrator: save approved draft",
            save_start,
        )

        record_orchestration_event(
            report_id=draft.report_id,
            action="approved_report_saved",
            status=ResearchStatus.APPROVED,
            details=str(saved_path),
        )

        return ResearchResult(
            report_id=draft.report_id,
            objective=draft.objective,
            status=ResearchStatus.APPROVED,
            content=draft.content,
            approved_to_save=True,
            tools_used=draft.tools_used,
            unique_tools_used=draft.unique_tools_used,
            saved_path=str(saved_path),
        )

    except Exception as error:
        error_message = str(error)

        record_orchestration_event(
            report_id=draft.report_id,
            action="report_save_failed",
            status=ResearchStatus.FAILED,
            details=error_message,
        )

        return ResearchResult(
            report_id=draft.report_id,
            objective=draft.objective,
            status=ResearchStatus.FAILED,
            content=draft.content,
            approved_to_save=False,
            tools_used=draft.tools_used,
            unique_tools_used=draft.unique_tools_used,
            error=error_message,
        )