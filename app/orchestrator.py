from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from app.agents.research_agent import build_agent


MIN_OBJECTIVE_LENGTH = 10
MAX_OBJECTIVE_LENGTH = 500


MAX_EXECUTION_SECONDS = 90

AUDIT_LOG_PATH = Path("reports/audit_log.jsonl")


class ResearchStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass
class ResearchResult:
    report_id: str
    status: ResearchStatus
    content: str
    approved_to_save: bool
    tools_used: list[str]
    unique_tools_used: list[str]
    error: str | None = None

    def to_dict(self) -> dict:
        result = asdict(self)
        result["status"] = self.status.value
        return result

def validate_objective(question: str) -> str:
    """
    Validate and clean the research objective.

    Rejects:
    - Empty objectives
    - Objectives that are too short
    - Objectives that are too long
    - Known overly broad objectives
    """
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
            f"Research objective cannot exceed "
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


def record_orchestration_event(
    report_id: str,
    action: str,
    status: ResearchStatus,
    details: str | None = None,
) -> None:
    """
    Record an orchestration event linked to one report ID.
    """
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


async def run_research(
    question: str,
    approved_to_save: bool = False,
) -> ResearchResult:
    """
    Run one isolated EvidenceOps research request.

    Approval belongs only to this function call.
    A new agent is created for every request.
    """
    report_id = f"report-{uuid4().hex[:12]}"
    status = ResearchStatus.DRAFT
    tools_used: list[str] = []

    try:
        objective = validate_objective(question)

        record_orchestration_event(
            report_id=report_id,
            action="research_started",
            status=status,
            details=objective,
        )

        agent = build_agent(
            approved_to_save=approved_to_save,
            tools_used=tools_used,
        )

        if approved_to_save:
            approval_instruction = (
                "The user has explicitly approved saving the final "
                "report for this request only. The save_report tool "
                "is available. Save only the final evidence-grounded "
                "report, not intermediate notes."
            )
        else:
            approval_instruction = (
                "The user has not approved saving. The save_report "
                "tool is unavailable. Return a draft response and "
                "request explicit approval before saving."
            )

        prompt = f"""
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
- Do not claim that a report was saved unless the save_report tool
  completed successfully.
- Include the research identifier {report_id} in any audit event.
- Clearly distinguish retrieved evidence, inference, and recommendation.
- State when the indexed evidence is incomplete or unavailable.

Use these response headings exactly once:
## Findings
## Evidence Limitations
## Confidence
## Next Action
"""

        async with asyncio.timeout(
            MAX_EXECUTION_SECONDS
        ):
            result = await agent.run(
                user_msg=prompt
            )

        if approved_to_save:
            status = ResearchStatus.APPROVED
            completed_action = "approved_research_completed"
        else:
            status = ResearchStatus.AWAITING_APPROVAL
            completed_action = "draft_research_completed"

        content = str(result)

        record_orchestration_event(
            report_id=report_id,
            action=completed_action,
            status=status,
        )

        return ResearchResult(
            report_id=report_id,
            status=status,
            content=content,
            approved_to_save=approved_to_save,
            tools_used=tools_used,
            unique_tools_used=list(dict.fromkeys(tools_used)),
        )

    except TimeoutError:
        status = ResearchStatus.FAILED

        error_message = (
            f"Research execution exceeded "
            f"{MAX_EXECUTION_SECONDS} seconds."
        )

        record_orchestration_event(
            report_id=report_id,
            action="research_timeout",
            status=status,
            details=error_message,
        )

        return ResearchResult(
            report_id=report_id,
            status=status,
            content="",
            approved_to_save=approved_to_save,
            tools_used=tools_used,
            unique_tools_used=list(dict.fromkeys(tools_used)),
            error=error_message,
        )