import pytest
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import Document, DocumentChunk, Subject
from app.seed import seed_academic_subjects, seed_vaigai_college


@pytest.mark.asyncio
async def test_seed_academic_subjects_lifecycle():
    # 1. Run base college seed
    await seed_vaigai_college()

    # 2. Run new subject seeder
    await seed_academic_subjects()

    async with AsyncSessionLocal() as session:
        # Verify core subjects are present
        res = await session.execute(select(Subject))
        subjects = res.scalars().all()
        codes = [s.code for s in subjects]

        # Expected seeded subjects across departments
        expected_codes = ["CS302", "CS401", "CS405", "EC201", "ME201", "IT201"]
        for expected in expected_codes:
            assert expected in codes, f"Expected subject {expected} to be seeded"

        # Verify documents and chunks exist for these subjects
        for s in subjects:
            if s.code in expected_codes:
                doc_count = await session.scalar(
                    select(func.count(Document.id)).where(Document.subject_id == s.id)
                )
                assert doc_count >= 1, f"Subject {s.code} must have at least 1 document"

                chunk_count = await session.scalar(
                    select(func.count(DocumentChunk.id)).where(DocumentChunk.subject_id == s.id)
                )
                assert chunk_count >= 1, f"Subject {s.code} must have at least 1 chunk"

        initial_count = len(subjects)

    # 3. Test idempotency: running again should not duplicate subjects
    await seed_academic_subjects()

    async with AsyncSessionLocal() as session:
        second_count = await session.scalar(select(func.count(Subject.id)))
        assert second_count == initial_count
