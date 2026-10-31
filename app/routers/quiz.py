from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sbac import enforce_subject_access
from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.models import BattleUsageCounter
from app.schemas import QuizStartRequest, QuizStartResponse, QuizSubmitRequest, QuizSubmitResponse
from app.services.quiz_engine import start_quiz_battle, submit_quiz_battle

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

@router.post("/start", response_model=QuizStartResponse)
async def start_quiz(
    req: QuizStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_subject_access(current_user, req.subject_id)

    # Check daily battle limit (Max 3 battles per day per PRD Section 5.11)
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    counter_res = await db.execute(
        select(BattleUsageCounter).where(
            BattleUsageCounter.student_id == current_user.id,
            BattleUsageCounter.date_str == today_str
        )
    )
    counter = counter_res.scalar_one_or_none()

    if counter and counter.battle_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit reached: Maximum 3 Quiz Battles allowed per calendar day. Resets at midnight."
        )

    if not counter:
        counter = BattleUsageCounter(
            student_id=current_user.id,
            date_str=today_str,
            battle_count=1
        )
        db.add(counter)
    else:
        counter.battle_count += 1

    await db.commit()

    return await start_quiz_battle(subject_id=req.subject_id, db=db)

@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    req: QuizSubmitRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    return await submit_quiz_battle(
        battle_id=req.battle_id,
        answers=req.answers,
        time_taken_seconds=req.time_taken_seconds
    )
