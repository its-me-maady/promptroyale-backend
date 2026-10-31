import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_quiz_battle_generate_10_mcqs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start Quiz Battle on CS101
        res = await ac.post(
            "/api/quiz/start",
            headers=headers,
            json={"subject_id": 1}
        )
        assert res.status_code == 200
        data = res.json()
        assert "battle_id" in data
        assert len(data["questions"]) == 10
        q1 = data["questions"][0]
        assert "id" in q1
        assert "question" in q1
        assert len(q1["options"]) == 4
        assert "source_citation" in q1
        assert len(q1["source_citation"]) > 0

@pytest.mark.asyncio
async def test_quiz_battle_submit_score():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start battle
        start_res = await ac.post(
            "/api/quiz/start",
            headers=headers,
            json={"subject_id": 1}
        )
        battle_data = start_res.json()
        battle_id = battle_data["battle_id"]

        # Submit answers
        answers = [{"question_id": q["id"], "selected_option": 0} for q in battle_data["questions"]]
        sub_res = await ac.post(
            "/api/quiz/submit",
            headers=headers,
            json={"battle_id": battle_id, "answers": answers, "time_taken_seconds": 45}
        )
        assert sub_res.status_code == 200
        result = sub_res.json()
        assert "score" in result
        assert "total" in result
        assert result["total"] == 10
        assert "accuracy_percentage" in result
        assert len(result["review"]) == 10
