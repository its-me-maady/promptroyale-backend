import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_chat_grounded_query_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Adhithiyan login
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask BFS question on CS101
        res = await ac.post(
            "/api/chat/query",
            headers=headers,
            json={"subject_id": 1, "question": "How does BFS traversal work in a binary tree?"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert len(data["answer"]) > 10
        assert data["is_insufficient_evidence"] is False
        assert len(data["citations"]) > 0
        citation = data["citations"][0]
        assert "document_title" in citation
        assert "Breadth-First Search" in citation["section_title"] or "Tree" in citation["document_title"]

@pytest.mark.asyncio
async def test_chat_insufficient_evidence_fallback():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ask off-topic question with zero academic basis
        res = await ac.post(
            "/api/chat/query",
            headers=headers,
            json={"subject_id": 1, "question": "Who won the 2024 FIFA World Cup in football?"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_insufficient_evidence"] is True
        assert "Insufficient academic evidence" in data["answer"]
