
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sbac import enforce_subject_access
from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.models import Document, Subject
from app.schemas import DocumentOut, SubjectOut

router = APIRouter(prefix="/api/subjects", tags=["subjects"])

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
        # Count documents
        doc_count_res = await db.execute(
            select(func.count(Document.id)).where(Document.subject_id == s.id)
        )
        doc_count = doc_count_res.scalar() or 0
        out.append(SubjectOut(
            id=s.id,
            name=s.name,
            code=s.code,
            description=s.description,
            department_id=s.department_id,
            document_count=doc_count
        ))
    return out

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
