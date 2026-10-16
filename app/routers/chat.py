import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..agent.graph import run_agent
from ..audit import log_event
from ..config import get_settings
from ..db import get_db
from ..models import ChatMessage, User, utcnow
from ..schemas import HistoryItem, QueryRequest, QueryResponse
from ..security import client_ip, get_current_user, rate_limiter

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> QueryResponse:
    """Run the LangGraph workflow. Identity/role come only from the verified token."""
    ip = client_ip(request)

    allowed, retry_after = rate_limiter.check(f"chat:{user.username}", settings.rate_limit_chat_per_minute)
    if not allowed:
        log_event(db, actor=user.username, role=user.role, action="chat_rate_limited", decision="deny", detail=f"retry after {retry_after}s", ip=ip)
        raise HTTPException(429, f"Rate limit exceeded. Try again in {retry_after} seconds.", headers={"Retry-After": str(retry_after)})

    result = run_agent(question=payload.question, username=user.username, role=user.role, full_name=user.full_name, ip=ip)

    db.add(
        ChatMessage(
            ts=utcnow(),
            username=user.username,
            role=user.role,
            question=payload.question,
            answer=result["answer"],
            route=result["route"],
            blocked=result["blocked"],
            citations_json=json.dumps(result["citations"]),
        )
    )
    db.commit()

    action = "query_blocked" if result["blocked"] else "policy_query"
    decision = "deny" if result["blocked"] else "allow"
    detail = payload.question[:200]
    if result["blocked"]:
        detail = f"[{result['guard_reason']}] {detail}"
    log_event(db, actor=user.username, role=user.role, action=action, resource=f"route={result['route']}", decision=decision, detail=detail, ip=ip)

    return QueryResponse(**result)


@router.get("/history", response_model=list[HistoryItem])
def history(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[HistoryItem]:
    limit = max(1, min(limit, 100))
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.username == user.username)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [HistoryItem.model_validate(row) for row in rows]
