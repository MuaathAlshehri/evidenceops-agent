from fastapi.testclient import TestClient

import app.api.main as api_main


client = TestClient(api_main.app)


class FakeResearchResult:
    def __init__(
        self,
        error=None,
        approved_to_save=False,
    ):
        self.error = error
        self.approved_to_save = approved_to_save

    def to_dict(self) -> dict:
        return {
            "report_id": "test-report-001",
            "status": "awaiting_approval",
            "content": "Test research result",
            "approved_to_save": self.approved_to_save,
            "error": self.error,
        }


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_research_endpoint_accepts_valid_request(monkeypatch) -> None:
    async def fake_run_research(
        question: str,
        approved_to_save: bool,
    ):
        assert question == "What is EvidenceOps?"
        assert approved_to_save is False

        return FakeResearchResult(
            approved_to_save=approved_to_save,
        )

    monkeypatch.setattr(
        api_main,
        "run_research",
        fake_run_research,
    )

    response = client.post(
        "/research",
        json={
            "question": "What is EvidenceOps?",
            "require_approval": True,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["report_id"] == "test-report-001"
    assert data["status"] == "awaiting_approval"
    assert data["approved_to_save"] is False
    assert data["error"] is None


def test_research_endpoint_rejects_invalid_request() -> None:
    response = client.post(
        "/research",
        json={},
    )

    assert response.status_code == 422