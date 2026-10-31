from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sbac import enforce_subject_access
from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import ChatQueryRequest, ChatQueryResponse
from app.services.rag_engine import query_rag_engine

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    req: ChatQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Enforce SBAC: student can only query enrolled subjects
    enforce_subject_access(current_user, req.subject_id)

    # Perform grounded retrieval
    return await query_rag_engine(
        subject_id=req.subject_id,
        question=req.question,
        db=db
    )
