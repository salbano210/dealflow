"""SQLAlchemy ORM models.

Design notes:
- `extracted_attributes` uses EAV (entity-attribute-value): adding a KPI
  in config/kpis.yaml requires no schema change.
- `llm_calls` logs every model invocation with cost -- observability +
  cost dashboard + eval-replay source.
- Every AI-derived value references the raw source it came from,
  satisfying the provenance requirement.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    airtable_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    raw_sources: Mapped[list["RawSource"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    attributes: Mapped[list["ExtractedAttribute"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    screenings: Mapped[list["Screening"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class RawSource(Base):
    """Unstructured evidence: CIM PDFs, scraped web pages, news, user notes."""
    __tablename__ = "raw_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # cim | website | news | user_note
    trust_tier: Mapped[int] = mapped_column(Integer, default=2)  # higher = more trusted (merge priority)
    url_or_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    text_blob: Mapped[str] = mapped_column(Text)
    allow_external_llm: Mapped[bool] = mapped_column(Boolean, default=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="raw_sources")


class ExtractedAttribute(Base):
    """EAV: one KPI value for one company at one point in time.

    Rows are never mutated in place. Current value = newest row with the
    highest trust_tier for a (company, kpi_key) pair -- computed at read.
    """
    __tablename__ = "extracted_attributes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    kpi_key: Mapped[str] = mapped_column(String(64), index=True)
    value_json: Mapped[dict] = mapped_column(JSON)  # {"value": ..., "state": "known"|"inferred"|"unknown"}
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("raw_sources.id"), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id"), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="attributes")


class Screening(Base):
    __tablename__ = "screenings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    thesis_version: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Float)
    passed_hard_filters: Mapped[bool] = mapped_column(Boolean, default=True)
    hard_filter_failures: Mapped[list] = mapped_column(JSON, default=list)
    model_config_snapshot: Mapped[dict] = mapped_column(JSON)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    company: Mapped[Company] = relationship(back_populates="screenings")
    dimensions: Mapped[list["ScreeningDimension"]] = relationship(
        back_populates="screening", cascade="all, delete-orphan"
    )


class ScreeningDimension(Base):
    __tablename__ = "screening_dimensions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    screening_id: Mapped[int] = mapped_column(ForeignKey("screenings.id"), index=True)
    dim_key: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_source_ids: Mapped[list] = mapped_column(JSON, default=list)
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id"), nullable=True)

    screening: Mapped[Screening] = relationship(back_populates="dimensions")


class ResearchQuestion(Base):
    __tablename__ = "research_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # NB: no send functionality. Approval only marks a draft ready for the human.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Decision(Base):
    """Audit log of human decisions."""
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class LlmCall(Base):
    """One row per LLM invocation. Never delete -- this is the eval corpus."""
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
