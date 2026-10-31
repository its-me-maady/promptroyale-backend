from datetime import UTC, datetime

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_key, encrypt_key, mask_key
from app.core.security import CurrentUser, get_current_user
from app.database import get_db
from app.models import AIProviderCredential
from app.schemas import AIProviderCredentialCreate, AIProviderCredentialOut

router = APIRouter(prefix="/api/students/credentials", tags=["credentials"])

SUPPORTED_PROVIDERS = {"gemini", "openai", "anthropic", "deepseek", "openrouter"}


def enforce_student(current_user: CurrentUser):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only enrolled students may manage BYOK AI provider credentials."
        )


@router.get("", response_model=list[AIProviderCredentialOut])
async def list_credentials(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_student(current_user)

    res = await db.execute(
        select(AIProviderCredential)
        .where(
            AIProviderCredential.student_id == current_user.id,
            AIProviderCredential.status == "active"
        )
        .order_by(AIProviderCredential.created_at.desc())
    )
    creds = res.scalars().all()

    out = []
    for c in creds:
        try:
            raw = decrypt_key(c.encrypted_key)
            masked = mask_key(raw)
        except (InvalidToken, ValueError):
            masked = "••••••••"

        out.append(AIProviderCredentialOut(
            id=c.id,
            student_id=c.student_id,
            provider=c.provider,
            masked_key=masked,
            status=c.status,
            is_default=bool(c.is_default),
            created_at=c.created_at
        ))
    return out


@router.post("", response_model=AIProviderCredentialOut)
async def create_or_update_credential(
    payload: AIProviderCredentialCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_student(current_user)

    provider_clean = payload.provider.lower().strip()
    if provider_clean not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{payload.provider}'. Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )

    if not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    # If setting as default, unmark other credentials for this student
    if payload.is_default:
        existing_creds_res = await db.execute(
            select(AIProviderCredential).where(AIProviderCredential.student_id == current_user.id)
        )
        for ec in existing_creds_res.scalars().all():
            ec.is_default = False

    # Check if a credential for this provider already exists
    res = await db.execute(
        select(AIProviderCredential).where(
            AIProviderCredential.student_id == current_user.id,
            AIProviderCredential.provider == provider_clean
        )
    )
    existing = res.scalars().first()

    encrypted = encrypt_key(payload.api_key.strip())
    masked = mask_key(payload.api_key.strip())

    if existing:
        existing.encrypted_key = encrypted
        existing.status = "active"
        existing.is_default = payload.is_default
        existing.created_at = datetime.now(UTC)
        cred = existing
    else:
        cred = AIProviderCredential(
            student_id=current_user.id,
            provider=provider_clean,
            encrypted_key=encrypted,
            status="active",
            is_default=payload.is_default,
            created_at=datetime.now(UTC)
        )
        db.add(cred)

    await db.commit()
    await db.refresh(cred)

    return AIProviderCredentialOut(
        id=cred.id,
        student_id=cred.student_id,
        provider=cred.provider,
        masked_key=masked,
        status=cred.status,
        is_default=bool(cred.is_default),
        created_at=cred.created_at
    )


@router.delete("/{credential_id}")
async def revoke_credential(
    credential_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    enforce_student(current_user)

    cred = await db.get(AIProviderCredential, credential_id)
    if not cred or cred.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Credential not found")

    await db.delete(cred)
    await db.commit()

    return {"message": f"Credential for {cred.provider} successfully revoked.", "id": credential_id}
