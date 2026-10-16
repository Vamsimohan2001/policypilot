import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    # request context (identity comes from the verified token only)
    question: str
    username: str
    full_name: str
    role: str
    ip: str

    # guard
    blocked: bool
    refusal: str
    guard_reason: str

    # routing
    route: str  # policy | smalltalk | out_of_scope | blocked

    # tool output
    retrieved: list[dict]

    # answer + verification
    answer: str
    citations: list[dict]
    citation_ok: bool
    evidence_retry: bool
    attempts: int

    # observability
    trace: Annotated[list[dict], operator.add]
