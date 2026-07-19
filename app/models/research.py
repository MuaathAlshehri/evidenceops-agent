from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(
        min_length=10,
        max_length=500,
    )

    audience: str | None = None
    require_approval: bool = True