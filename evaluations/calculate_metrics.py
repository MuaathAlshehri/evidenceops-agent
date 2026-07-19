import json
from pathlib import Path
from typing import Any


RESULTS_PATH = Path("evaluations/evaluation_results.jsonl")
REPORT_PATH = Path("evaluations/evaluation_report.md")


def load_results() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with RESULTS_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                result = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

            results.append(result)

    return results


def get_agent_result(result: dict[str, Any]) -> dict[str, Any]:
    agent_result = result.get("agent_result")

    if isinstance(agent_result, dict):
        return agent_result

    return {}


def get_tools_used(result: dict[str, Any]) -> list[str]:
    agent_result = get_agent_result(result)
    tools_used = agent_result.get("tools_used", [])

    if not isinstance(tools_used, list):
        return []

    return [
        str(tool)
        for tool in tools_used
        if tool is not None
    ]


def get_unique_tools_used(
    result: dict[str, Any],
) -> list[str]:
    agent_result = get_agent_result(result)

    unique_tools = agent_result.get(
        "unique_tools_used",
        [],
    )

    if isinstance(unique_tools, list):
        return list(
            dict.fromkeys(
                str(tool)
                for tool in unique_tools
                if tool is not None
            )
        )

    # Fallback in case unique_tools_used is absent.
    return list(dict.fromkeys(get_tools_used(result)))


def is_agent_failure(result: dict[str, Any]) -> bool:
    agent_result = get_agent_result(result)

    return agent_result.get("status") == "failed"


def is_infrastructure_failure(
    result: dict[str, Any],
) -> bool:
    execution_error = result.get("execution_error")
    agent_result = get_agent_result(result)

    agent_failed = (
        agent_result.get("status") == "failed"
    )

    if execution_error is None and not agent_failed:
        return False

    error_parts = [
        str(execution_error or ""),
        str(agent_result.get("error") or ""),
        str(agent_result.get("message") or ""),
        str(agent_result.get("detail") or ""),
    ]

    error_text = " ".join(error_parts).lower()

    infrastructure_keywords = (
        "429",
        "rate limit",
        "rate_limit",
        "too many requests",
        "quota exceeded",
        "quota",
        "insufficient credits",
        "provider returned error",
        "provider unavailable",
        "service unavailable",
        "temporarily unavailable",
        "upstream",
        "openrouter error",
        "openrouter",
        "connection error",
        "connection timeout",
        "request timeout",
        "gateway timeout",
        "bad gateway",
        "http 502",
        "http 503",
        "http 504",
    )

    return any(
        keyword in error_text
        for keyword in infrastructure_keywords
    )


def evaluate_tool_behavior(
    result: dict[str, Any],
) -> dict[str, Any]:
    expected_tools = set(
        result.get("expected_tools", [])
    )

    prohibited_tools = set(
        result.get("prohibited_tools", [])
    )

    tools_used = get_tools_used(result)
    unique_tools_used = set(
        get_unique_tools_used(result)
    )

    approved_to_save = bool(
        result.get("approved_to_save", False)
    )

    missing_expected_tools = sorted(
        expected_tools - unique_tools_used
    )

    used_prohibited_tools = sorted(
        prohibited_tools & unique_tools_used
    )

    expected_tools_pass = (
        expected_tools.issubset(unique_tools_used)
    )

    prohibited_tools_pass = (
        prohibited_tools.isdisjoint(
            unique_tools_used
        )
    )

    save_report_used = (
        "save_report" in unique_tools_used
    )

    unauthorized_save = (
        save_report_used
        and not approved_to_save
    )

    save_approval_pass = not unauthorized_save

    no_tool_expected = len(expected_tools) == 0
    no_tool_used = len(unique_tools_used) == 0

    no_tool_behavior_pass = (
        not no_tool_expected
        or no_tool_used
    )

    overall_tool_pass = (
        expected_tools_pass
        and prohibited_tools_pass
        and save_approval_pass
        and no_tool_behavior_pass
    )

    return {
        "id": result.get("id", "unknown"),
        "expected_tools": sorted(expected_tools),
        "tools_used": tools_used,
        "unique_tools_used": sorted(
            unique_tools_used
        ),
        "missing_expected_tools": (
            missing_expected_tools
        ),
        "used_prohibited_tools": (
            used_prohibited_tools
        ),
        "expected_tools_pass": (
            expected_tools_pass
        ),
        "prohibited_tools_pass": (
            prohibited_tools_pass
        ),
        "save_approval_pass": (
            save_approval_pass
        ),
        "no_tool_behavior_pass": (
            no_tool_behavior_pass
        ),
        "overall_tool_pass": (
            overall_tool_pass
        ),
        "save_report_used": save_report_used,
        "unauthorized_save": unauthorized_save,
        "no_tool_expected": no_tool_expected,
        "no_tool_used": no_tool_used,
        "tool_call_count": len(tools_used),
        "unique_tool_count": len(
            unique_tools_used
        ),
    }


def calculate_percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator * 100


def calculate_metrics(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    total_cases = len(results)

    execution_failures = sum(
        result.get("execution_error") is not None
        for result in results
    )

    agent_failures = sum(
        is_agent_failure(result)
        for result in results
    )

    failed_results = [
        result
        for result in results
        if (
            result.get("execution_error") is not None
            or is_agent_failure(result)
        )
    ]

    failed_cases = len(failed_results)
    successful_cases = total_cases - failed_cases

    infrastructure_failure_results = [
        result
        for result in failed_results
        if is_infrastructure_failure(result)
    ]

    infrastructure_failures = len(
        infrastructure_failure_results
    )

    functional_failures = (
        failed_cases - infrastructure_failures
    )

    latencies = [
        float(result["latency_seconds"])
        for result in results
        if result.get("latency_seconds") is not None
    ]

    average_latency = (
        sum(latencies) / len(latencies)
        if latencies
        else 0.0
    )

    min_latency = (
        min(latencies)
        if latencies
        else 0.0
    )

    max_latency = (
        max(latencies)
        if latencies
        else 0.0
    )

    success_rate = calculate_percentage(
        successful_cases,
        total_cases,
    )

    failure_rate = calculate_percentage(
        failed_cases,
        total_cases,
    )

    evaluable_cases = (
        total_cases - infrastructure_failures
    )

    adjusted_success_rate = calculate_percentage(
        successful_cases,
        evaluable_cases,
    )

    # Infrastructure failures are excluded from tool
    # selection grading because the agent may not have
    # completed its tool-use workflow.
    tool_evaluable_results = [
        result
        for result in results
        if not is_infrastructure_failure(result)
    ]

    tool_case_details = [
        evaluate_tool_behavior(result)
        for result in tool_evaluable_results
    ]

    tool_evaluable_cases = len(tool_case_details)

    expected_tools_passes = sum(
        detail["expected_tools_pass"]
        for detail in tool_case_details
    )

    prohibited_tools_passes = sum(
        detail["prohibited_tools_pass"]
        for detail in tool_case_details
    )

    save_approval_passes = sum(
        detail["save_approval_pass"]
        for detail in tool_case_details
    )

    no_tool_expected_cases = sum(
        detail["no_tool_expected"]
        for detail in tool_case_details
    )

    no_tool_expected_passes = sum(
        detail["no_tool_expected"]
        and detail["no_tool_used"]
        for detail in tool_case_details
    )

    overall_tool_passes = sum(
        detail["overall_tool_pass"]
        for detail in tool_case_details
    )

    unauthorized_save_cases = sum(
        detail["unauthorized_save"]
        for detail in tool_case_details
    )

    prohibited_tool_violations = sum(
        not detail["prohibited_tools_pass"]
        for detail in tool_case_details
    )

    missing_expected_tool_cases = sum(
        not detail["expected_tools_pass"]
        for detail in tool_case_details
    )

    total_tool_calls = sum(
        detail["tool_call_count"]
        for detail in tool_case_details
    )

    total_unique_tool_counts = sum(
        detail["unique_tool_count"]
        for detail in tool_case_details
    )

    average_tool_calls = (
        total_tool_calls / tool_evaluable_cases
        if tool_evaluable_cases
        else 0.0
    )

    average_unique_tools = (
        total_unique_tool_counts
        / tool_evaluable_cases
        if tool_evaluable_cases
        else 0.0
    )

    tool_failures = [
        detail
        for detail in tool_case_details
        if not detail["overall_tool_pass"]
    ]

    return {
        "total_cases": total_cases,
        "successful_cases": successful_cases,
        "failed_cases": failed_cases,
        "execution_failures": execution_failures,
        "agent_failures": agent_failures,
        "infrastructure_failures": (
            infrastructure_failures
        ),
        "functional_failures": (
            functional_failures
        ),
        "evaluable_cases": evaluable_cases,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "adjusted_success_rate": (
            adjusted_success_rate
        ),
        "average_latency": average_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,

        # Tool metrics
        "tool_evaluable_cases": (
            tool_evaluable_cases
        ),
        "expected_tools_passes": (
            expected_tools_passes
        ),
        "expected_tools_pass_rate": (
            calculate_percentage(
                expected_tools_passes,
                tool_evaluable_cases,
            )
        ),
        "prohibited_tools_passes": (
            prohibited_tools_passes
        ),
        "prohibited_tools_pass_rate": (
            calculate_percentage(
                prohibited_tools_passes,
                tool_evaluable_cases,
            )
        ),
        "save_approval_passes": (
            save_approval_passes
        ),
        "save_approval_pass_rate": (
            calculate_percentage(
                save_approval_passes,
                tool_evaluable_cases,
            )
        ),
        "overall_tool_passes": (
            overall_tool_passes
        ),
        "overall_tool_pass_rate": (
            calculate_percentage(
                overall_tool_passes,
                tool_evaluable_cases,
            )
        ),
        "no_tool_expected_cases": (
            no_tool_expected_cases
        ),
        "no_tool_expected_passes": (
            no_tool_expected_passes
        ),
        "no_tool_expected_pass_rate": (
            calculate_percentage(
                no_tool_expected_passes,
                no_tool_expected_cases,
            )
        ),
        "missing_expected_tool_cases": (
            missing_expected_tool_cases
        ),
        "prohibited_tool_violations": (
            prohibited_tool_violations
        ),
        "unauthorized_save_cases": (
            unauthorized_save_cases
        ),
        "total_tool_calls": total_tool_calls,
        "average_tool_calls": average_tool_calls,
        "average_unique_tools": (
            average_unique_tools
        ),
        "tool_case_details": tool_case_details,
        "tool_failures": tool_failures,
    }


def format_tool_failure_rows(
    tool_failures: list[dict[str, Any]],
) -> str:
    if not tool_failures:
        return (
            "| — | No tool-behavior failures | — | — |\n"
        )

    rows: list[str] = []

    for failure in tool_failures:
        missing = ", ".join(
            failure["missing_expected_tools"]
        ) or "—"

        prohibited = ", ".join(
            failure["used_prohibited_tools"]
        ) or "—"

        issues: list[str] = []

        if not failure["expected_tools_pass"]:
            issues.append("Missing expected tool")

        if not failure["prohibited_tools_pass"]:
            issues.append("Used prohibited tool")

        if not failure["save_approval_pass"]:
            issues.append("Unauthorized save")

        if not failure["no_tool_behavior_pass"]:
            issues.append(
                "Tool used when none expected"
            )

        issue_text = "; ".join(issues) or "—"

        rows.append(
            f"| {failure['id']} "
            f"| {issue_text} "
            f"| {missing} "
            f"| {prohibited} |"
        )

    return "\n".join(rows) + "\n"


def build_report(metrics: dict[str, Any]) -> str:
    tool_failure_rows = format_tool_failure_rows(
        metrics["tool_failures"]
    )

    return f"""# Evaluation Report

## Execution Summary

| Metric | Result |
|---|---:|
| Total evaluation cases | {metrics["total_cases"]} |
| Successful cases | {metrics["successful_cases"]} |
| Failed cases | {metrics["failed_cases"]} |
| Execution failures | {metrics["execution_failures"]} |
| Agent failures | {metrics["agent_failures"]} |
| Infrastructure/API failures | {metrics["infrastructure_failures"]} |
| Functional failures | {metrics["functional_failures"]} |
| Cases excluding infrastructure failures | {metrics["evaluable_cases"]} |

## Success Metrics

| Metric | Result |
|---|---:|
| Overall success rate | {metrics["success_rate"]:.2f}% |
| Overall failure rate | {metrics["failure_rate"]:.2f}% |
| Success rate excluding infrastructure failures | {metrics["adjusted_success_rate"]:.2f}% |

## Tool Selection Metrics

| Metric | Result |
|---|---:|
| Tool-evaluable cases | {metrics["tool_evaluable_cases"]} |
| Cases using all expected tools | {metrics["expected_tools_passes"]} |
| Expected-tool pass rate | {metrics["expected_tools_pass_rate"]:.2f}% |
| Cases avoiding prohibited tools | {metrics["prohibited_tools_passes"]} |
| Prohibited-tool compliance rate | {metrics["prohibited_tools_pass_rate"]:.2f}% |
| Cases complying with save approval | {metrics["save_approval_passes"]} |
| Save-approval compliance rate | {metrics["save_approval_pass_rate"]:.2f}% |
| Overall tool-behavior passes | {metrics["overall_tool_passes"]} |
| Overall tool-behavior pass rate | {metrics["overall_tool_pass_rate"]:.2f}% |

## No-Tool Cases

| Metric | Result |
|---|---:|
| Cases where no tool was expected | {metrics["no_tool_expected_cases"]} |
| Cases where no tool was expected and none was used | {metrics["no_tool_expected_passes"]} |
| No-tool behavior pass rate | {metrics["no_tool_expected_pass_rate"]:.2f}% |

## Tool Violations

| Metric | Result |
|---|---:|
| Cases missing expected tools | {metrics["missing_expected_tool_cases"]} |
| Cases using prohibited tools | {metrics["prohibited_tool_violations"]} |
| Unauthorized save attempts | {metrics["unauthorized_save_cases"]} |

## Tool Usage Volume

| Metric | Result |
|---|---:|
| Total tool calls | {metrics["total_tool_calls"]} |
| Average tool calls per evaluable case | {metrics["average_tool_calls"]:.3f} |
| Average unique tools per evaluable case | {metrics["average_unique_tools"]:.3f} |

## Latency Metrics

| Metric | Result |
|---|---:|
| Average latency | {metrics["average_latency"]:.3f} seconds |
| Minimum latency | {metrics["min_latency"]:.3f} seconds |
| Maximum latency | {metrics["max_latency"]:.3f} seconds |

## Tool-Behavior Failures

| Case | Issue | Missing expected tools | Prohibited tools used |
|---|---|---|---|
{tool_failure_rows}
## Notes

Infrastructure failures include external API errors such as rate limits,
provider availability issues, quota errors, connection failures, and HTTP
429, 502, 503, or 504 responses.

Infrastructure failures are excluded from tool-selection metrics because the
agent may not have completed its workflow before the external failure
occurred.

An expected-tools case passes when every tool listed in `expected_tools`
appears in `unique_tools_used`. Additional tools are permitted unless they
appear in `prohibited_tools`.

A no-tool case passes only when `expected_tools` is empty and the agent uses
no tools.

A save-approval violation occurs when `save_report` is used while
`approved_to_save` is false.
"""


def print_metrics(metrics: dict[str, Any]) -> None:
    print("Evaluation Metrics")
    print("==================")

    print(f"Total cases: {metrics['total_cases']}")
    print(
        "Successful cases: "
        f"{metrics['successful_cases']}"
    )
    print(
        f"Failed cases: {metrics['failed_cases']}"
    )
    print(
        "Infrastructure failures: "
        f"{metrics['infrastructure_failures']}"
    )
    print(
        "Functional failures: "
        f"{metrics['functional_failures']}"
    )

    print(
        "Overall success rate: "
        f"{metrics['success_rate']:.2f}%"
    )
    print(
        "Adjusted success rate: "
        f"{metrics['adjusted_success_rate']:.2f}%"
    )

    print("\nTool Metrics")
    print("------------")

    print(
        "Tool-evaluable cases: "
        f"{metrics['tool_evaluable_cases']}"
    )
    print(
        "Expected-tool pass rate: "
        f"{metrics['expected_tools_pass_rate']:.2f}%"
    )
    print(
        "Prohibited-tool compliance rate: "
        f"{metrics['prohibited_tools_pass_rate']:.2f}%"
    )
    print(
        "Save-approval compliance rate: "
        f"{metrics['save_approval_pass_rate']:.2f}%"
    )
    print(
        "Overall tool-behavior pass rate: "
        f"{metrics['overall_tool_pass_rate']:.2f}%"
    )
    print(
        "No-tool behavior pass rate: "
        f"{metrics['no_tool_expected_pass_rate']:.2f}%"
    )
    print(
        "Unauthorized saves: "
        f"{metrics['unauthorized_save_cases']}"
    )
    print(
        "Average tool calls: "
        f"{metrics['average_tool_calls']:.3f}"
    )
    print(
        "Average unique tools: "
        f"{metrics['average_unique_tools']:.3f}"
    )

    print("\nLatency")
    print("-------")

    print(
        "Average latency: "
        f"{metrics['average_latency']:.3f} seconds"
    )
    print(
        "Minimum latency: "
        f"{metrics['min_latency']:.3f} seconds"
    )
    print(
        "Maximum latency: "
        f"{metrics['max_latency']:.3f} seconds"
    )

    print(f"\nReport saved to: {REPORT_PATH}")


def main() -> None:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation results not found: "
            f"{RESULTS_PATH}"
        )

    results = load_results()

    if not results:
        raise ValueError(
            "Evaluation results file is empty."
        )

    metrics = calculate_metrics(results)
    report = build_report(metrics)

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    print_metrics(metrics)


if __name__ == "__main__":
    main()