from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..audit import log_event
from ..db import get_db
from ..models import AuditLog, User
from ..policies import load_policy_index
from ..schemas import DocumentDetail, DocumentHistoryItem, DocumentSummary, DocumentsOverview, RestrictedDocument
from ..security import client_ip, get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=DocumentsOverview)
def list_documents(user: User = Depends(get_current_user)) -> DocumentsOverview:
    accessible: list[DocumentSummary] = []
    restricted: list[RestrictedDocument] = []
    for doc in load_policy_index():
        if user.role in doc["roles"]:
            accessible.append(
                DocumentSummary(
                    doc_id=doc["id"],
                    title=doc["title"],
                    category=doc["category"],
                    version=doc["version"],
                    effective_date=doc["effective_date"],
                    owner=doc["owner"],
                    roles=doc["roles"],
                )
            )
        else:
            restricted.append(RestrictedDocument(doc_id=doc["id"], title=doc["title"]))
    return DocumentsOverview(accessible=accessible, restricted=restricted, role=user.role)


@router.get("/history", response_model=list[DocumentHistoryItem])
def view_history(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentHistoryItem]:
    """Documents the current user has opened, most recent view per document first."""
    limit = max(1, min(limit, 100))
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.actor == user.username, AuditLog.action == "document_view")
        .order_by(AuditLog.id.desc())
        .limit(limit * 5)
        .all()
    )
    titles = {doc["id"]: doc["title"] for doc in load_policy_index()}
    seen: set[str] = set()
    out: list[DocumentHistoryItem] = []
    for row in rows:
        if row.resource in seen:
            continue
        seen.add(row.resource)
        out.append(DocumentHistoryItem(ts=row.ts, doc_id=row.resource, title=titles.get(row.resource, row.resource)))
        if len(out) >= limit:
            break
    return out


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    doc = next((d for d in load_policy_index() if d["id"].lower() == doc_id.lower()), None)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if user.role not in doc["roles"]:
        log_event(db, actor=user.username, role=user.role, action="document_denied", resource=doc["id"], decision="deny", detail=f"role '{user.role}' not in {doc['roles']}", ip=client_ip(request))
        raise HTTPException(status_code=403, detail="Your role does not have access to this document.")

    log_event(db, actor=user.username, role=user.role, action="document_view", resource=doc["id"], decision="allow", detail=f"viewed '{doc['title']}'", ip=client_ip(request))
    return DocumentDetail(
        doc_id=doc["id"],
        title=doc["title"],
        category=doc["category"],
        version=doc["version"],
        effective_date=doc["effective_date"],
        owner=doc["owner"],
        roles=doc["roles"],
        content=doc["content"],
    )
