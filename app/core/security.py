from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(
    user_id: int,
    email: str,
    role: str,
    college_id: int,
    department_id: int | None,
    enrolled_subjects: list[int],
    expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "college_id": college_id,
        "department_id": department_id,
        "enrolled_subjects": enrolled_subjects,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

class CurrentUser:
    def __init__(self, user_id: int, email: str, role: str, college_id: int, department_id: int | None, enrolled_subjects: list[int]):
        self.id = user_id
        self.email = email
        self.role = role
        self.college_id = college_id
        self.department_id = department_id
        self.enrolled_subjects = enrolled_subjects

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> CurrentUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        role = payload.get("role")
        college_id = int(payload.get("college_id", 0))
        department_id = payload.get("department_id")
        enrolled_subjects = payload.get("enrolled_subjects", [])
        return CurrentUser(
            user_id=user_id,
            email=email,
            role=role,
            college_id=college_id,
            department_id=department_id,
            enrolled_subjects=enrolled_subjects
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
