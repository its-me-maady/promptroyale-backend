from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, subjects
from app.seed import seed_vaigai_college


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed Vaigai College data automatically
    await init_db()
    await seed_vaigai_college()
    yield

app = FastAPI(
    title="Prompt Royale API",
    description="College Academic AI Platform Backend Service - Vaigai College",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(subjects.router)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "promptroyale-backend",
        "version": "0.1.0",
        "institution": "Vaigai College of Engineering"
    }
