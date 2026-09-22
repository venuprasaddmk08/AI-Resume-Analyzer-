from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 - ensures models are registered on Base before create_all
from api import resume
from config import get_settings
from database import Base, engine

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume & Career Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api/resume", tags=["resume"])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "ai_available": settings.ai_available,
    }
