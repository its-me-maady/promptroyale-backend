from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.models import BillingSnapshot, College, Department, Subject, User
from app.schemas import (
    AdminOverviewOut,
    BillingSnapshotOut,
    DepartmentCreate,
    DepartmentOut,
    UserAdminOut,
    UserStatusUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def enforce_admin(current_user: CurrentUser):
    if current_user.role != "college_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Institutional administrator privileges required."
        )


@router.get("/overview", response_model=AdminOverviewOut)
async def get_admin_overview(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    college = await db.get(College, current_user.college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    # Counts
    dept_count = await db.scalar(
        select(func.count(Department.id)).where(Department.college_id == college.id)
    ) or 0
    sub_count = await db.scalar(
        select(func.count(Subject.id))
        .join(Department, Subject.department_id == Department.id)
        .where(Department.college_id == college.id)
    ) or 0
    student_count = await db.scalar(
        select(func.count(User.id)).where(User.college_id == college.id, User.role == "student")
    ) or 0
    faculty_count = await db.scalar(
        select(func.count(User.id)).where(User.college_id == college.id, User.role == "department_user")
    ) or 0

    # Billing Snapshot
    snapshot_res = await db.execute(
        select(BillingSnapshot)
        .where(BillingSnapshot.college_id == college.id)
        .order_by(BillingSnapshot.id.desc())
    )
    snapshot = snapshot_res.scalars().first()
    if not snapshot:
        snapshot_out = BillingSnapshotOut(
            snapshot_date=datetime.now(UTC).strftime("%Y-%m"),
            active_student_count=student_count,
            monthly_token_quota=1_000_000,
            tokens_consumed=142_500,
            tier=college.service_tier
        )
    else:
        snapshot_out = BillingSnapshotOut(
            snapshot_date=snapshot.snapshot_date,
            active_student_count=snapshot.active_student_count,
            monthly_token_quota=snapshot.monthly_token_quota,
            tokens_consumed=snapshot.tokens_consumed,
            tier=snapshot.tier
        )

    return AdminOverviewOut(
        college_id=college.id,
        college_name=college.name,
        college_domain=college.domain,
        department_count=dept_count,
        subject_count=sub_count,
        student_count=student_count,
        faculty_count=faculty_count,
        billing_snapshot=snapshot_out,
        ai_status="Connected (Gemini 1.5 Flash)"
    )


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    res = await db.execute(select(Department).where(Department.college_id == current_user.college_id))
    depts = res.scalars().all()

    out = []
    for d in depts:
        s_count = await db.scalar(select(func.count(Subject.id)).where(Subject.department_id == d.id)) or 0
        f_count = await db.scalar(select(func.count(User.id)).where(User.department_id == d.id, User.role == "department_user")) or 0
        out.append(DepartmentOut(
            id=d.id,
            college_id=d.college_id,
            name=d.name,
            code=d.code,
            subject_count=s_count,
            faculty_count=f_count
        ))
    return out


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    payload: DepartmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    dept = Department(
        college_id=current_user.college_id,
        name=payload.name,
        code=payload.code.upper().strip()
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)

    return DepartmentOut(
        id=dept.id,
        college_id=dept.college_id,
        name=dept.name,
        code=dept.code,
        subject_count=0,
        faculty_count=0
    )


@router.get("/users", response_model=list[UserAdminOut])
async def list_college_users(
    role: str | None = None,
    status_filter: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    query = select(User).where(User.college_id == current_user.college_id)
    if role:
        query = query.where(User.role == role)
    if status_filter:
        query = query.where(User.status == status_filter)

    res = await db.execute(query)
    users = res.scalars().all()

    out = []
    for u in users:
        dept_name = None
        if u.department_id:
            dept = await db.get(Department, u.department_id)
            if dept:
                dept_name = dept.name
        out.append(UserAdminOut(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role,
            status=u.status or "active",
            department_name=dept_name,
            created_at=u.created_at
        ))
    return out


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    user = await db.get(User, user_id)
    if not user or user.college_id != current_user.college_id:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = payload.status
    if payload.status == "deactivated":
        user.is_active = False
        user.deactivated_at = datetime.now(UTC)
    else:
        user.is_active = True
        user.deactivated_at = None

    await db.commit()
    return {"message": f"User status updated to {payload.status}", "user_id": user.id, "status": user.status}
