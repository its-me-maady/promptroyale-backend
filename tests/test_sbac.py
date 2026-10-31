import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_sbac_student_allowed_subject():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Adhithiyan logs in (enrolled in CS101)
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query subjects visible to student
        subjects_res = await ac.get("/api/subjects", headers=headers)
        assert subjects_res.status_code == 200
        subjects = subjects_res.json()
        subject_codes = [s["code"] for s in subjects]
        assert "CS101" in subject_codes
        # CS202 should not be in student's enrolled subjects list
        assert "CS202" not in subject_codes

@pytest.mark.asyncio
async def test_sbac_student_denied_unauthorized_subject():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Adhithiyan logs in
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Find CS202 ID from all subjects or test subject verification endpoint
        verify_res = await ac.get("/api/subjects/2/verify-access", headers=headers)
        assert verify_res.status_code == 403
        assert "Subject access denied" in verify_res.json()["detail"]

@pytest.mark.asyncio
async def test_sbac_faculty_access_department_subjects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Faculty logs in
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "faculty.cse@vaigai.edu", "password": "Vaigai@123"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Faculty sees all department subjects (CS101 and CS202)
        subjects_res = await ac.get("/api/subjects", headers=headers)
        assert subjects_res.status_code == 200
        subject_codes = [s["code"] for s in subjects_res.json()]
        assert "CS101" in subject_codes
        assert "CS202" in subject_codes
