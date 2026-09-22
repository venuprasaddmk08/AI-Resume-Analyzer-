from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    normalized_text: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    tables: Mapped[list] = mapped_column(JSON, default=list)
    sections: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(10))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_text: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    tables: Mapped[list] = mapped_column(JSON, default=list)
    sections: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
