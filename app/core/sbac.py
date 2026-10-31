from fastapi import HTTPException, status

from app.core.security import CurrentUser


def enforce_subject_access(current_user: CurrentUser, subject_id: int):
    """
    Subject-Based Access Control (SBAC):
    - Students can ONLY access subjects they are currently enrolled in.
    - If a student attempts to access any unassigned subject, reject with 403 Forbidden.
    - Department staff and College Administrators have access within their institution scope.
    """
    if current_user.role == "student" and subject_id not in current_user.enrolled_subjects:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subject access denied: Student {current_user.email} is not enrolled in subject ID {subject_id}.",
        )
    return True
