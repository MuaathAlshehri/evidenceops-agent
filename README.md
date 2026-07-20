# EvidenceOps Agentic-RAG

An Agentic Retrieval-Augmented Generation (RAG) system for AI governance and cybersecurity research. The project combines deterministic routing, vector search, and LLM-powered synthesis to generate structured, evidence-based reports through a FastAPI service.

---

## Features

- Agentic RAG architecture
- FastAPI REST API
- Smart request routing
- Parallel comparison workflow
- Single-topic research workflow
- Identity & capability responses
- Approval workflow before saving reports
- Persistent vector index
- Configurable LLM and embedding models

---

## Architecture

```
                User
                  │
                  ▼
              FastAPI API
                  │
                  ▼
           Research Orchestrator
                  │
     ┌────────────┼────────────┐
     │            │            │
 Identity    Single Topic   Comparison
     │            │            │
     └────────────┼────────────┘
                  │
          Function Agent (Fallback)
                  │
                  ▼
           Retrieval Pipeline
                  │
                  ▼
            VectorStoreIndex
                  │
                  ▼
              LLM Synthesis
                  │
                  ▼
            Research Report
```

---

## API Endpoints

### Generate Research

```
POST /research
```

Example request

```json
{
  "question": "Explain the NIST AI Risk Management Framework.",
  "audience": "developer",
  "require_approval": true
}
```

---

### Approve Report

```
POST /research/{report_id}/approve
```

---

### Health Check

```
GET /health
```

---

## Technology Stack

- Python
- FastAPI
- LlamaIndex
- ChromaDB
- Google Gemini
- Pydantic
- Uvicorn

---

## Project Structure

```
app/
│
├── api/
├── orchestrator/
├── agents/
├── services/
├── tools/
├── prompts/
├── config/
└── models/
```

---

## Current Workflows

- Identity requests
- Single-topic research
- Parallel framework comparison
- Agent-based fallback workflow
- Approval before persistence

---

## Future Improvements

- Semantic intent classification
- Capability routing
- Multi-agent orchestration
- PostgreSQL draft storage
- Authentication & authorization
- Streaming responses

---

## Author

Muath AL Biryaa

