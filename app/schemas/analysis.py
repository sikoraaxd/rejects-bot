from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    case_id: str = Field(
        default="",
        description="Case id, project, employee, or free-text lookup.",
    )
    project_name: str = Field(default="", description="Название проекта.")
    manual_context: str = Field(default="", description="Дополнительный ручной контекст.")
    force_refresh: bool = Field(default=False, description="Игнорировать локальный кэш.")


class SourceDocument(BaseModel):
    title: str = Field(default="", description="Название источника.")
    text: str = Field(default="", description="Извлеченный текст источника.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные источника.")


class CaseOption(BaseModel):
    id: str = Field(..., description="Stable case identifier.")
    label: str = Field(..., description="Human-readable case label.")
    project_name: str = Field(default="", description="Project name.")
    employee: str = Field(default="", description="Candidate or employee name.")
    technology: str = Field(default="", description="Technology or role.")
    grade: str = Field(default="", description="Candidate grade.")
    source: str = Field(default="", description="Source/status column value.")
    date: str = Field(default="", description="Case date.")
    sheet: str = Field(default="", description="Source sheet name.")
    review_url: str = Field(default="", description="Expert analysis Google Sheet URL.")
    comment: str = Field(default="", description="Reject comment text.")


class CaseRow(BaseModel):
    unk: str = ""
    spc: str = ""
    project_name: str = ""
    employee: str = ""
    technology: str = ""
    grade: str = ""
    source: str = ""
    demand: str = ""
    commentary: str = ""
    expert_analyze: str = ""
    readiness: str = ""
    date: str = ""
    sheet: str = ""


class CaseOptionsResponse(BaseModel):
    items: list[CaseRow] = Field(default_factory=list)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class RejectionAnalysis(BaseModel):
    summary: str = Field(..., description="Short rejection summary.")
    primary_reason: str = Field(..., description="Primary rejection reason.")
    reason_categories: list[str] = Field(..., description="Reason categories.")
    evidence: list[str] = Field(..., description="Evidence from source text.")
    project_mismatch: list[str] = Field(..., description="Project mismatch points.")
    candidate_gaps: list[str] = Field(..., description="Candidate gaps.")
    recommendations: list[str] = Field(..., description="Recommendations.")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score from 0 to 1.")


class AnalysisResponse(BaseModel):
    id: str = Field(..., description="Analysis id.")
    case_id: str = Field(default="", description="Case lookup key.")
    project_name: str = Field(default="", description="Project name.")
    created_at: datetime = Field(..., description="Analysis creation timestamp.")
    source: SourceDocument = Field(..., description="Source document data.")
    similar_cases: list[dict[str, Any]] = Field(..., description="RAG similar cases.")
    analysis: RejectionAnalysis = Field(..., description="Rejection analysis result.")
    cached: bool = Field(default=False, description="Whether response came from cache.")


class AnalysisListItem(BaseModel):
    id: str = Field(..., description="Analysis id.")
    case_id: str = Field(default="", description="Case lookup key.")
    project_name: str = Field(default="", description="Project name.")
    created_at: datetime = Field(..., description="Analysis creation timestamp.")
    primary_reason: str = Field(..., description="Primary rejection reason.")
    confidence: float = Field(..., description="Confidence score.")


class ChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(
        default_factory=list,
        description="История сообщений чата.",
    )
    context: str = Field(default="", description="Дополнительная информация.")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Agent answer.")
