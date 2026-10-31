import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app


@pytest.mark.asyncio
async def test_database_url_required():
    # If DATABASE_URL is explicitly set to empty or None, Settings must raise an error
    with pytest.raises((ValueError, RuntimeError)):
        Settings(DATABASE_URL="")


@pytest.mark.asyncio
async def test_admin_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Admin
        admin_login = await client.post(
            "/api/auth/login",
            json={"email": "admin@vaigai.edu", "password": "Vaigai@123"}
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Get Admin Overview
        res_overview = await client.get("/api/admin/overview", headers=admin_headers)
        assert res_overview.status_code == 200
        data = res_overview.json()
        assert "department_count" in data
        assert "subject_count" in data
        assert "student_count" in data
        assert "faculty_count" in data
        assert "billing_snapshot" in data

        # 3. Create Department with faculty credentials
        unique_dept_code = f"IT_{uuid.uuid4().hex[:4].upper()}"
        faculty_email = f"faculty_{uuid.uuid4().hex[:4]}@vaigai.edu"
        res_create_dept = await client.post(
            "/api/admin/departments",
            headers=admin_headers,
            json={
                "name": "Information Technology",
                "code": unique_dept_code,
                "faculty_name": "Dr. S. Kumar",
                "faculty_email": faculty_email,
                "faculty_password": "Vaigai@123"
            }
        )
        assert res_create_dept.status_code == 200
        dept_data = res_create_dept.json()
        assert dept_data["code"] == unique_dept_code
        assert dept_data["lead_faculty_email"] == faculty_email
        dept_id = dept_data["id"]

        # 4. Verify newly created faculty can log in
        new_faculty_login = await client.post(
            "/api/auth/login",
            json={"email": faculty_email, "password": "Vaigai@123"}
        )
        assert new_faculty_login.status_code == 200
        assert new_faculty_login.json()["user"]["role"] == "department_user"

        # 5. Edit Department via PUT /api/admin/departments/{id}
        res_update_dept = await client.put(
            f"/api/admin/departments/{dept_id}",
            headers=admin_headers,
            json={"name": "Information Technology & Systems"}
        )
        assert res_update_dept.status_code == 200
        assert res_update_dept.json()["name"] == "Information Technology & Systems"

        # 6. List Departments
        res_depts = await client.get("/api/admin/departments", headers=admin_headers)
        assert res_depts.status_code == 200
        codes = [d["code"] for d in res_depts.json()]
        assert "CSE" in codes
        assert unique_dept_code in codes

        # 7. Non-admin forbidden
        faculty_login = await client.post(
            "/api/auth/login",
            json={"email": "faculty.cse@vaigai.edu", "password": "Vaigai@123"}
        )
        faculty_token = faculty_login.json()["access_token"]
        faculty_headers = {"Authorization": f"Bearer {faculty_token}"}
        res_forbidden = await client.get("/api/admin/overview", headers=faculty_headers)
        assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_student_and_subject_management():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Faculty
        faculty_login = await client.post(
            "/api/auth/login",
            json={"email": "faculty.cse@vaigai.edu", "password": "Vaigai@123"}
        )
        assert faculty_login.status_code == 200
        faculty_token = faculty_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {faculty_token}"}

        # 1. Create a new Subject
        res_create_sub = await client.post(
            "/api/subjects",
            headers=headers,
            json={
                "code": "CS301",
                "name": "Design & Analysis of Algorithms",
                "description": "Divide and conquer, greedy methods, and dynamic programming."
            }
        )
        assert res_create_sub.status_code == 200
        new_sub = res_create_sub.json()
        assert new_sub["code"] == "CS301"
        sub_id = new_sub["id"]

        # 2. Add a new Student
        unique_email = f"priya_{uuid.uuid4().hex[:6]}@vaigai.edu"
        res_create_stu = await client.post(
            "/api/students",
            headers=headers,
            json={
                "name": "Priya Raman",
                "email": unique_email,
                "password": "Vaigai@123",
                "initial_subject_ids": [sub_id]
            }
        )
        assert res_create_stu.status_code == 200
        student = res_create_stu.json()
        student_id = student["id"]
        assert unique_email in student["email"]
        assert sub_id in student["enrolled_subjects"]

        # 3. List Students in Department
        res_list_stu = await client.get("/api/students", headers=headers)
        assert res_list_stu.status_code == 200
        emails = [s["email"] for s in res_list_stu.json()]
        assert unique_email in emails
        assert "adhithiyan@vaigai.edu" in emails

        # 4. Remove Subject Membership (Unenroll)
        res_del = await client.delete(
            f"/api/students/{student_id}/subjects/{sub_id}",
            headers=headers
        )
        assert res_del.status_code == 200

        # 5. Check Subject Enrolled Students list
        res_sub_students = await client.get(
            f"/api/subjects/{sub_id}/students",
            headers=headers
        )
        assert res_sub_students.status_code == 200
        enrolled_ids = [s["id"] for s in res_sub_students.json()["enrolled"]]
        assert student_id not in enrolled_ids
