from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sbac import enforce_subject_access
from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.models import Document, Subject, SubjectMembership, User
from app.schemas import (
    DocumentOut,
    StudentDetailOut,
    SubjectCreate,
    SubjectOut,
    SubjectStudentsOut,
    SubjectUpdate,
)

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def enforce_staff(current_user: CurrentUser):
    if current_user.role not in ("department_user", "college_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Staff privileges required to modify subjects."
        )


@router.get("", response_model=list[SubjectOut])
async def list_subjects(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Subject)
    # SBAC: If student, restrict to assigned subject memberships
    if current_user.role == "student":
        query = query.where(Subject.id.in_(current_user.enrolled_subjects))
    elif current_user.role == "department_user" and current_user.department_id:
        query = query.where(Subject.department_id == current_user.department_id)

    result = await db.execute(query)
    subjects = result.scalars().all()

    out = []
    for s in subjects:
        doc_count = await db.scalar(
            select(func.count(Document.id)).where(Document.subject_id == s.id)
        ) or 0
        stu_count = await db.scalar(
            select(func.count(SubjectMembership.id)).where(
                SubjectMembership.subject_id == s.id,
                SubjectMembership.status == "active",
                SubjectMembership.is_active.is_(True)
            )
        ) or 0
        out.append(SubjectOut(
            id=s.id,
            name=s.name,
            code=s.code,
            description=s.description,
            department_id=s.department_id,
            document_count=doc_count,
            enrolled_student_count=stu_count
        ))
    return out


@router.post("", response_model=SubjectOut)
async def create_subject(
    payload: SubjectCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    dept_id = payload.department_id or current_user.department_id
    if not dept_id:
        raise HTTPException(status_code=400, detail="Department ID is required.")

    subject = Subject(
        department_id=dept_id,
        code=payload.code.upper().strip(),
        name=payload.name.strip(),
        description=payload.description
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)

    return SubjectOut(
        id=subject.id,
        name=subject.name,
        code=subject.code,
        description=subject.description,
        department_id=subject.department_id,
        document_count=0,
        enrolled_student_count=0
    )


@router.put("/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    if payload.code:
        subject.code = payload.code.upper().strip()
    if payload.name:
        subject.name = payload.name.strip()
    if payload.description is not None:
        subject.description = payload.description.strip()

    await db.commit()
    await db.refresh(subject)

    doc_count = await db.scalar(
        select(func.count(Document.id)).where(Document.subject_id == subject.id)
    ) or 0
    stu_count = await db.scalar(
        select(func.count(SubjectMembership.id)).where(
            SubjectMembership.subject_id == subject.id,
            SubjectMembership.status == "active",
            SubjectMembership.is_active.is_(True)
        )
    ) or 0

    return SubjectOut(
        id=subject.id,
        name=subject.name,
        code=subject.code,
        description=subject.description,
        department_id=subject.department_id,
        document_count=doc_count,
        enrolled_student_count=stu_count
    )


@router.get("/{subject_id}/students", response_model=SubjectStudentsOut)
async def get_subject_students(
    subject_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)

    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    # Fetch all students in department
    students_res = await db.execute(
        select(User).where(
            User.college_id == current_user.college_id,
            User.role == "student",
            User.department_id == subject.department_id
        )
    )
    all_students = students_res.scalars().all()

    # Fetch enrolled student ids
    mem_res = await db.execute(
        select(SubjectMembership.student_id).where(
            SubjectMembership.subject_id == subject.id,
            SubjectMembership.status == "active",
            SubjectMembership.is_active.is_(True)
        )
    )
    enrolled_student_ids = set(mem_res.scalars().all())

    enrolled = []
    available = []
    for s in all_students:
        s_out = StudentDetailOut(
            id=s.id,
            email=s.email,
            name=s.name,
            role=s.role,
            status=s.status or "active",
            enrolled_subjects=[subject.id] if s.id in enrolled_student_ids else [],
            enrolled_subject_details=[]
        )
        if s.id in enrolled_student_ids:
            enrolled.append(s_out)
        else:
            available.append(s_out)

    return SubjectStudentsOut(
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        enrolled=enrolled,
        available_students=available
    )


@router.post("/{subject_id}/students")
async def add_student_to_subject(
    subject_id: int,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_staff(current_user)
    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    mem_res = await db.execute(
        select(SubjectMembership).where(
            SubjectMembership.student_id == student_id,
            SubjectMembership.subject_id == subject_id
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
            student_id=student_id,
            subject_id=subject_id,
            status="active",
            is_active=True,
            added_at=datetime.now(UTC)
        )
        db.add(membership)

    await db.commit()
    return {"message": "Student enrolled in subject", "student_id": student_id, "subject_id": subject_id}


@router.delete("/{subject_id}/students/{student_id}")
async def remove_student_from_subject(
    subject_id: int,
    student_id: int,
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
        raise HTTPException(status_code=404, detail="Membership not found.")

    membership.status = "removed"
    membership.is_active = False
    membership.removed_at = datetime.now(UTC)

    await db.commit()
    return {"message": "Student removed from subject", "student_id": student_id, "subject_id": subject_id}


@router.get("/{subject_id}/verify-access")
async def verify_subject_access(
    subject_id: int,
    current_user: CurrentUser = Depends(get_current_user)
):
    enforce_subject_access(current_user, subject_id)
    return {"status": "authorized", "subject_id": subject_id, "user": current_user.email}


@router.get("/{subject_id}/documents", response_model=list[DocumentOut])
async def list_subject_documents(
    subject_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_subject_access(current_user, subject_id)
    result = await db.execute(select(Document).where(Document.subject_id == subject_id))
    docs = result.scalars().all()
    return [
        DocumentOut(
            id=d.id,
            title=d.title,
            subject_id=d.subject_id,
            file_type=d.file_type,
            processing_status=d.processing_status
        )
        for d in docs
    ]
