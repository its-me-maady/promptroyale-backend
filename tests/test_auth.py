import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_auth_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "Vaigai@123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "adhithiyan@vaigai.edu"
        assert data["user"]["role"] == "student"
        assert len(data["user"]["enrolled_subjects"]) > 0

@pytest.mark.asyncio
async def test_auth_login_invalid_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"email": "adhithiyan@vaigai.edu", "password": "WrongPassword"}
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_auth_me_authenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First login
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "faculty.cse@vaigai.edu", "password": "Vaigai@123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # Call /me
        me_res = await ac.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_res.status_code == 200
        user_info = me_res.json()
        assert user_info["email"] == "faculty.cse@vaigai.edu"
        assert user_info["role"] == "department_user"

@pytest.mark.asyncio
async def test_auth_me_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/auth/me")
        assert response.status_code == 401
