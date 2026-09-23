from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 - ensures models are registered on Base before create_all
from api import analysis, jobs, resume
from config import get_settings
from database import Base, engine
from services import semantic_matcher

settings = get_settings()

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Starts the local semantic-similarity model downloading/loading in
    # the background right away, so it has the time between server boot
    # and a user's first analysis request to finish — rather than only
    # starting on that first request and racing its own timeout budget.
    semantic_matcher.start_background_load()
    yield


app = FastAPI(title="AI Resume & Career Intelligence Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "ai_available": settings.ai_available,
    }
