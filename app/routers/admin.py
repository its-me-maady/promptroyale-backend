from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user, get_password_hash
from app.database import get_db
from app.models import (
    BattleUsageCounter,
    BillingSnapshot,
    College,
    Department,
    Subject,
    SubjectMembership,
    UsageRecord,
    User,
)
from app.schemas import (
    AdminOverviewOut,
    BillingSnapshotOut,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    StaffCreate,
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
        staff_res = await db.execute(
            select(User).where(User.department_id == d.id, User.role == "department_user")
        )
        dept_staff = staff_res.scalars().all()
        f_count = len(dept_staff)
        assigned_ids = [u.id for u in dept_staff]
        lead_faculty = dept_staff[0].email if dept_staff else None

        out.append(DepartmentOut(
            id=d.id,
            college_id=d.college_id,
            name=d.name,
            code=d.code,
            subject_count=s_count,
            faculty_count=f_count,
            lead_faculty_email=lead_faculty,
            assigned_staff_ids=assigned_ids
        ))
    return out


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    payload: DepartmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    if payload.faculty_email:
        existing = await db.scalar(select(User).where(User.email == payload.faculty_email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A user with email {payload.faculty_email} already exists."
            )

    dept = Department(
        college_id=current_user.college_id,
        name=payload.name.strip(),
        code=payload.code.upper().strip()
    )
    db.add(dept)
    await db.flush()

    # Provision initial faculty account if provided
    lead_email = None
    if payload.faculty_email and payload.faculty_password:
        faculty_user = User(
            college_id=current_user.college_id,
            department_id=dept.id,
            email=payload.faculty_email,
            name=payload.faculty_name.strip() if payload.faculty_name else f"{dept.code} Faculty",
            hashed_password=get_password_hash(payload.faculty_password),
            role="department_user",
            status="active",
            is_active=True
        )
        db.add(faculty_user)
        lead_email = payload.faculty_email

    # Assign selected staff members
    if payload.staff_ids:
        for s_id in payload.staff_ids:
            staff = await db.get(User, s_id)
            if staff and staff.college_id == current_user.college_id and staff.role == "department_user":
                staff.department_id = dept.id

    await db.commit()
    await db.refresh(dept)

    # Fetch assigned staff
    staff_res = await db.execute(
        select(User).where(User.department_id == dept.id, User.role == "department_user")
    )
    assigned_staff = staff_res.scalars().all()
    assigned_ids = [u.id for u in assigned_staff]
    if not lead_email and assigned_staff:
        lead_email = assigned_staff[0].email

    return DepartmentOut(
        id=dept.id,
        college_id=dept.college_id,
        name=dept.name,
        code=dept.code,
        subject_count=0,
        faculty_count=len(assigned_ids),
        lead_faculty_email=lead_email,
        assigned_staff_ids=assigned_ids
    )


@router.put("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    dept = await db.get(Department, department_id)
    if not dept or dept.college_id != current_user.college_id:
        raise HTTPException(status_code=404, detail="Department not found")

    if payload.code:
        dept.code = payload.code.upper().strip()
    if payload.name:
        dept.name = payload.name.strip()

    if payload.staff_ids is not None:
        # Unassign staff currently in this department but not in new list
        current_staff_res = await db.execute(
            select(User).where(User.department_id == dept.id, User.role == "department_user")
        )
        for u in current_staff_res.scalars().all():
            if u.id not in payload.staff_ids:
                u.department_id = None

        # Assign new staff
        for s_id in payload.staff_ids:
            staff = await db.get(User, s_id)
            if staff and staff.college_id == current_user.college_id and staff.role == "department_user":
                staff.department_id = dept.id

    await db.commit()
    await db.refresh(dept)

    s_count = await db.scalar(select(func.count(Subject.id)).where(Subject.department_id == dept.id)) or 0
    staff_res = await db.execute(
        select(User).where(User.department_id == dept.id, User.role == "department_user")
    )
    assigned_staff = staff_res.scalars().all()
    assigned_ids = [u.id for u in assigned_staff]
    lead_faculty = assigned_staff[0].email if assigned_staff else None

    return DepartmentOut(
        id=dept.id,
        college_id=dept.college_id,
        name=dept.name,
        code=dept.code,
        subject_count=s_count,
        faculty_count=len(assigned_ids),
        lead_faculty_email=lead_faculty,
        assigned_staff_ids=assigned_ids
    )


@router.get("/staff", response_model=list[UserAdminOut])
async def list_staff_members(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    res = await db.execute(
        select(User).where(User.college_id == current_user.college_id, User.role == "department_user")
    )
    staff_members = res.scalars().all()

    out = []
    for u in staff_members:
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
            department_id=u.department_id,
            department_name=dept_name,
            created_at=u.created_at
        ))
    return out


@router.post("/staff", response_model=UserAdminOut)
async def create_staff_member(
    payload: StaffCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with email {payload.email} already exists."
        )

    dept_name = None
    if payload.department_id:
        dept = await db.get(Department, payload.department_id)
        if not dept or dept.college_id != current_user.college_id:
            raise HTTPException(status_code=400, detail="Invalid department ID.")
        dept_name = dept.name

    staff = User(
        college_id=current_user.college_id,
        department_id=payload.department_id,
        email=payload.email,
        name=payload.name.strip(),
        hashed_password=get_password_hash(payload.password),
        role="department_user",
        status="active",
        is_active=True
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)

    return UserAdminOut(
        id=staff.id,
        email=staff.email,
        name=staff.name,
        role=staff.role,
        status=staff.status,
        department_id=staff.department_id,
        department_name=dept_name,
        created_at=staff.created_at
    )


@router.delete("/staff/{staff_id}")
async def delete_staff_member(
    staff_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    staff = await db.get(User, staff_id)
    if not staff or staff.college_id != current_user.college_id or staff.role != "department_user":
        raise HTTPException(status_code=404, detail="Staff member not found")

    await db.execute(delete(UsageRecord).where(UsageRecord.user_id == staff.id))
    await db.delete(staff)
    await db.commit()

    return {"message": "Staff member deleted successfully", "id": staff_id}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_admin(current_user)

    user = await db.get(User, user_id)
    if not user or user.college_id != current_user.college_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own administrator account.")

    # Clean up dependent tables
    await db.execute(delete(BattleUsageCounter).where(BattleUsageCounter.student_id == user.id))
    await db.execute(delete(UsageRecord).where(UsageRecord.user_id == user.id))
    await db.execute(delete(SubjectMembership).where(SubjectMembership.student_id == user.id))
    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully", "id": user_id}


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
