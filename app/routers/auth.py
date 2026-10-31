from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import SubjectMembership, User
from app.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: email or password incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated"
        )

    # Fetch enrolled subjects for student
    enrolled_ids = []
    if user.role == "student":
        mem_res = await db.execute(
            select(SubjectMembership.subject_id).where(
                SubjectMembership.student_id == user.id,
                SubjectMembership.is_active == True
            )
        )
        enrolled_ids = list(mem_res.scalars().all())

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        college_id=user.college_id,
        department_id=user.department_id,
        enrolled_subjects=enrolled_ids
    )

    user_out = UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        college_id=user.college_id,
        department_id=user.department_id,
        enrolled_subjects=enrolled_ids
    )

    return LoginResponse(access_token=token, token_type="bearer", user=user_out)

@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        college_id=user.college_id,
        department_id=user.department_id,
        enrolled_subjects=current_user.enrolled_subjects
    )
