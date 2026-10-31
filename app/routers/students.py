from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user, get_password_hash
from app.database import get_db
from app.models import (
    BattleUsageCounter,
    Subject,
    SubjectMembership,
    UsageRecord,
    User,
)
from app.schemas import (
    StudentCreate,
    StudentDetailOut,
    StudentEnrolledSubject,
    StudentUpdate,
    SubjectEnrollmentRequest,
)

router = APIRouter(prefix="/api/students", tags=["students"])


def enforce_staff(current_user: CurrentUser):
    if current_user.role not in ("department_user", "college_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Staff privileges required to manage students."
        )


@router.get("", response_model=list[StudentDetailOut])
async def list_department_students(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    query = select(User).where(User.college_id == current_user.college_id, User.role == "student")
    if current_user.role == "department_user" and current_user.department_id:
        query = query.where(User.department_id == current_user.department_id)

    res = await db.execute(query)
    students = res.scalars().all()

    out = []
    for s in students:
        # Load active subject memberships
        mem_res = await db.execute(
            select(Subject)
            .join(SubjectMembership, Subject.id == SubjectMembership.subject_id)
            .where(
                SubjectMembership.student_id == s.id,
                SubjectMembership.status == "active",
                SubjectMembership.is_active.is_(True)
            )
        )
        active_subs = mem_res.scalars().all()

        enrolled_ids = [sub.id for sub in active_subs]
        enrolled_details = [
            StudentEnrolledSubject(id=sub.id, code=sub.code, name=sub.name)
            for sub in active_subs
        ]

        out.append(StudentDetailOut(
            id=s.id,
            email=s.email,
            name=s.name,
            role=s.role,
            status=s.status or "active",
            enrolled_subjects=enrolled_ids,
            enrolled_subject_details=enrolled_details
        ))
    return out


@router.post("", response_model=StudentDetailOut)
async def create_student(
    payload: StudentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    # Check email duplicate
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    student = User(
        college_id=current_user.college_id,
        department_id=current_user.department_id,
        email=payload.email,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
        role="student",
        status="active",
        is_active=True
    )
    db.add(student)
    await db.flush()

    # Assign initial subjects
    enrolled_details = []
    enrolled_ids = []
    for sub_id in payload.initial_subject_ids:
        sub = await db.get(Subject, sub_id)
        if sub:
            membership = SubjectMembership(
                student_id=student.id,
                subject_id=sub.id,
                status="active",
                is_active=True,
                added_at=datetime.now(UTC)
            )
            db.add(membership)
            enrolled_ids.append(sub.id)
            enrolled_details.append(StudentEnrolledSubject(id=sub.id, code=sub.code, name=sub.name))

    await db.commit()
    await db.refresh(student)

    return StudentDetailOut(
        id=student.id,
        email=student.email,
        name=student.name,
        role=student.role,
        status=student.status,
        enrolled_subjects=enrolled_ids,
        enrolled_subject_details=enrolled_details
    )


@router.put("/{student_id}", response_model=StudentDetailOut)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    student = await db.get(User, student_id)
    if not student or student.college_id != current_user.college_id or student.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.name:
        student.name = payload.name
    if payload.status:
        student.status = payload.status
        if payload.status == "deactivated":
            student.is_active = False
            student.deactivated_at = datetime.now(UTC)
        else:
            student.is_active = True
            student.deactivated_at = None

    await db.commit()
    await db.refresh(student)

    # Fetch memberships
    mem_res = await db.execute(
        select(Subject)
        .join(SubjectMembership, Subject.id == SubjectMembership.subject_id)
        .where(
            SubjectMembership.student_id == student.id,
            SubjectMembership.status == "active",
            SubjectMembership.is_active.is_(True)
        )
    )
    active_subs = mem_res.scalars().all()

    return StudentDetailOut(
        id=student.id,
        email=student.email,
        name=student.name,
        role=student.role,
        status=student.status,
        enrolled_subjects=[sub.id for sub in active_subs],
        enrolled_subject_details=[
            StudentEnrolledSubject(id=sub.id, code=sub.code, name=sub.name)
            for sub in active_subs
        ]
    )


@router.post("/{student_id}/subjects")
async def enroll_student_in_subject(
    student_id: int,
    payload: SubjectEnrollmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    student = await db.get(User, student_id)
    if not student or student.college_id != current_user.college_id or student.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")

    subject = await db.get(Subject, payload.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Check if membership already exists
    mem_res = await db.execute(
        select(SubjectMembership).where(
            SubjectMembership.student_id == student.id,
            SubjectMembership.subject_id == subject.id
        )
    )
    membership = mem_res.scalars().first()

    if membership:
        membership.status = "active"
        membership.is_active = True
        membership.removed_at = None
        membership.added_at = datetime.now(UTC)
    else:
        membership = SubjectMembership(
            student_id=student.id,
            subject_id=subject.id,
            status="active",
            is_active=True,
            added_at=datetime.now(UTC)
        )
        db.add(membership)

    await db.commit()
    return {"message": f"Student {student.name} enrolled in {subject.code}", "student_id": student.id, "subject_id": subject.id}


@router.delete("/{student_id}/subjects/{subject_id}")
async def unenroll_student_from_subject(
    student_id: int,
    subject_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    mem_res = await db.execute(
        select(SubjectMembership).where(
            SubjectMembership.student_id == student_id,
            SubjectMembership.subject_id == subject_id
        )
    )
    membership = mem_res.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Subject membership not found")

    membership.status = "removed"
    membership.is_active = False
    membership.removed_at = datetime.now(UTC)

    await db.commit()
    return {"message": f"Student unenrolled from subject {subject_id}", "student_id": student_id, "subject_id": subject_id}


@router.delete("/{student_id}")
async def delete_student(
    student_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    student = await db.get(User, student_id)
    if not student or student.college_id != current_user.college_id or student.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")

    if (
        current_user.role == "department_user"
        and current_user.department_id
        and student.department_id != current_user.department_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot delete students outside your department."
        )

    # Clean up dependent records
    await db.execute(delete(BattleUsageCounter).where(BattleUsageCounter.student_id == student.id))
    await db.execute(delete(UsageRecord).where(UsageRecord.user_id == student.id))
    await db.execute(delete(SubjectMembership).where(SubjectMembership.student_id == student.id))
    await db.delete(student)
    await db.commit()

    return {"message": f"Student {student.name} deleted successfully", "student_id": student_id}
