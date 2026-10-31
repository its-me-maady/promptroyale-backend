import pytest
from sqlalchemy import delete

from app.database import AsyncSessionLocal, init_db
from app.models import BattleUsageCounter
from app.seed import seed_vaigai_college


@pytest.fixture(autouse=True)
async def initialize_test_database():
    await init_db()
    await seed_vaigai_college()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(BattleUsageCounter))
        await session.commit()
