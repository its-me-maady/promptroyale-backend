import pytest

from app.database import init_db
from app.seed import seed_vaigai_college


@pytest.fixture(autouse=True)
async def initialize_test_database():
    await init_db()
    await seed_vaigai_college()
