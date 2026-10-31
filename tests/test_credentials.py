import pytest
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal
from app.main import app
from app.models import AIProviderCredential


@pytest.mark.asyncio
async def test_student_multi_provider_byok_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Student (Adhithiyan)
        login_res = await client.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Add first provider: Gemini (SRS FR-7.2 Recommended)
        raw_gemini_key = "AIzaSyFakeGeminiKey1234567890ABCDEF"
        res_gemini = await client.post(
            "/api/students/credentials",
            headers=headers,
            json={
                "provider": "gemini",
                "api_key": raw_gemini_key,
                "is_default": True
            }
        )
        assert res_gemini.status_code == 200
        gemini_cred = res_gemini.json()
        assert gemini_cred["provider"] == "gemini"
        assert gemini_cred["status"] == "active"
        assert gemini_cred["masked_key"].startswith("AIza")
        assert raw_gemini_key not in gemini_cred["masked_key"]
        gemini_id = gemini_cred["id"]

        # 3. Add second provider: OpenAI
        raw_openai_key = "sk-proj-FakeOpenAIKey1234567890GHIJKL"
        res_openai = await client.post(
            "/api/students/credentials",
            headers=headers,
            json={
                "provider": "openai",
                "api_key": raw_openai_key,
                "is_default": False
            }
        )
        assert res_openai.status_code == 200
        openai_cred = res_openai.json()
        assert openai_cred["provider"] == "openai"
        assert openai_cred["status"] == "active"
        assert openai_cred["masked_key"].startswith("sk-p")
        openai_id = openai_cred["id"]

        # 4. List all configured credentials
        list_res = await client.get("/api/students/credentials", headers=headers)
        assert list_res.status_code == 200
        creds = list_res.json()
        providers = [c["provider"] for c in creds]
        assert "gemini" in providers
        assert "openai" in providers

        # 5. Verify encryption at rest in database (SRS FR-7.3, FR-7.5)
        async with AsyncSessionLocal() as session:
            db_gemini = await session.get(AIProviderCredential, gemini_id)
            assert db_gemini is not None
            # Plaintext key must NOT be stored directly in database
            assert db_gemini.encrypted_key != raw_gemini_key
            assert "FakeGeminiKey" not in db_gemini.encrypted_key

        # 6. Revoke/delete the OpenAI credential (SRS FR-7.6, FR-7.7)
        del_res = await client.delete(f"/api/students/credentials/{openai_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify list no longer contains revoked/deleted credential
        list_after_del = await client.get("/api/students/credentials", headers=headers)
        assert list_after_del.status_code == 200
        ids_after = [c["id"] for c in list_after_del.json()]
        assert openai_id not in ids_after
        assert gemini_id in ids_after

        # 7. Non-student cannot access credentials
        faculty_login = await client.post(
            "/api/auth/login",
            json={"email": "faculty.cse@vaigai.edu", "password": "Vaigai@123"}
        )
        faculty_token = faculty_login.json()["access_token"]
        faculty_headers = {"Authorization": f"Bearer {faculty_token}"}
        res_forbidden = await client.get("/api/students/credentials", headers=faculty_headers)
        assert res_forbidden.status_code == 403
