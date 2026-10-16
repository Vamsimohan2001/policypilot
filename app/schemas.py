from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=128)
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["employee", "hr", "admin"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------------------------------------------------------------- chat
class Citation(BaseModel):
    label: str
    doc_id: str
    title: str
    section: str
    snippet: str
    roles: list[str] = []


class TraceStep(BaseModel):
    step: int
    node: str
    status: str
    detail: str = ""
    ms: int = 0


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    blocked: bool
    route: str
    guard_reason: str | None = None
    citations: list[Citation] = []
    trace: list[TraceStep] = []
    latency_ms: int = 0


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    question: str
    answer: str
    route: str
    blocked: bool


# ---------------------------------------------------------------- documents
class DocumentSummary(BaseModel):
    doc_id: str
    title: str
    category: str
    version: str
    effective_date: str
    owner: str
    roles: list[str]
    accessible: bool = True


class RestrictedDocument(BaseModel):
    doc_id: str
    title: str


class DocumentsOverview(BaseModel):
    accessible: list[DocumentSummary]
    restricted: list[RestrictedDocument]
    role: str


class DocumentDetail(BaseModel):
    doc_id: str
    title: str
    category: str
    version: str
    effective_date: str
    owner: str
    roles: list[str]
    content: str


class DocumentHistoryItem(BaseModel):
    ts: datetime
    doc_id: str
    title: str


# ---------------------------------------------------------------- admin
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    actor: str
    role: str
    action: str
    resource: str
    decision: str
    detail: str
    ip: str


class UserAdminOut(BaseModel):
    username: str
    full_name: str
    role: str
    is_active: bool
    failed_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None


# ---------------------------------------------------------------- system
class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    llm_mode: str
    embedding_backend: str
    documents: int
    chunks: int
