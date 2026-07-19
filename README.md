# EvidenceOps Agent

## Overview

EvidenceOps Agent is an AI governance research agent designed to answer questions using a trusted knowledge base while enforcing safe tool usage and human approval for consequential actions.

The system retrieves evidence from indexed governance documents, compares multiple sources when needed, records audit events, and only saves reports after explicit user approval.

---

## Features

- Retrieval-Augmented Generation (RAG)
- Knowledge-base search
- Multi-document comparison
- Audit event recording
- Human approval before report saving
- Prompt injection resistance
- Tool usage tracking
- Evaluation framework with automated metrics

---

## Project Structure

```
app/
    agent.py
    tools.py
    prompts.py
    models.py
    retrieval.py
    ...

evaluations/
    evaluation_dataset.jsonl
    evaluation_results.jsonl
    evaluation_report.md
    run_evaluation.py
    calculate_metrics.py
    validate_dataset.py

knowledge_base/
    ...

reports/
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| knowledge_base_search | Retrieves relevant governance evidence |
| compare_sources | Compares evidence across multiple documents |
| record_audit_event | Records audit information |
| save_report | Saves a report after explicit approval |

---

## Human Approval Policy

The agent follows a strict approval policy.

The `save_report` tool is only executed when:

- the user explicitly approves saving the report, and
- `approved_to_save=True`.

Otherwise the report is generated only as a draft.

---

## Prompt Injection Protection

The agent treats retrieved documents as untrusted evidence.

Retrieved content is never allowed to:

- override system instructions
- reveal hidden prompts
- bypass approval requirements
- force tool execution

---

## Evaluation Framework

The project contains an automated evaluation pipeline.

### Dataset

```
evaluation_dataset.jsonl
```

Each evaluation case includes:

- question
- expected source
- expected tools
- prohibited tools
- grading notes
- approval state

Example:

```json
{
    "expected_tools": [
        "knowledge_base_search"
    ],
    "prohibited_tools": [
        "save_report"
    ]
}
```

---

### Running Evaluation

```bash
uv run python evaluations/run_evaluation.py
```

Results are written to:

```
evaluations/evaluation_results.jsonl
```

---

## Tool Evaluation Design

Instead of evaluating a single expected tool, the framework evaluates tool behavior using:

- expected_tools
- prohibited_tools
- tools_used
- unique_tools_used

The evaluation checks:

- Required tools were used.
- Prohibited tools were avoided.
- save_report follows approval requirements.
- Cases expecting no tools execute without tool calls.

This design better reflects realistic agent workflows where multiple tools may be required to complete a task.

---

### Calculating Metrics

```bash
uv run python evaluations/calculate_metrics.py
```

Generated report:

```
evaluations/evaluation_report.md
```

---

## Metrics

The evaluation reports:

- Overall success rate
- Infrastructure failures
- Functional failures
- Expected tool compliance
- Prohibited tool compliance
- Save approval compliance
- Tool behavior pass rate
- Tool usage statistics
- Latency metrics

---

## Validation

Validate the evaluation dataset before execution.

```bash
uv run python evaluations/validate_dataset.py
```

---

## Technologies

- Python 3.13
- OpenAI Agents SDK
- OpenRouter
- ChromaDB
- LangChain
- Sentence Transformers
- uv

---

## Workflow

```
User
    │
    ▼
Agent
    │
    ▼
Tool Selection
    │
    ├── knowledge_base_search
    ├── compare_sources
    ├── record_audit_event
    └── save_report
            │
            ▼
Approval Check
            │
      approved_to_save?
         │        │
        No       Yes
         │        │
         ▼        ▼
 Draft     Save Report
```

---

## Author

Muath Al-Buraya

Information Systems

Imam Mohammad Ibn Saud Islamic University