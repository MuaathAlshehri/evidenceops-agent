from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from app.orchestrator import ResearchResult,approve_and_save,run_research


app = FastAPI(title="EvidenceOps API")


class ResearchRequest(BaseModel):
    question: str
    audience: str = "general"
    require_approval: bool = True



draft_store: dict[str, ResearchResult] = {}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "EvidenceOps API",
    }

@app.post("/research")
async def research(request: ResearchRequest):
    result = await run_research(
        question=request.question,
    )

    if result.status.value == "awaiting_approval":
        draft_store[result.report_id] = result

    return jsonable_encoder(asdict(result))


@app.post("/research/{report_id}/approve")
async def approve_research(report_id: str):
    draft = draft_store.get(report_id)

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft report not found",
        )

    approved_result = await approve_and_save(draft)


    draft_store.pop(report_id, None)

    return jsonable_encoder(asdict(approved_result))