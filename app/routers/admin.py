from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..audit import log_event
from ..db import get_db
from ..models import AuditLog, User
from ..schemas import AuditOut, UserAdminOut
from ..security import ROLE_ADMIN, client_ip, require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    request: Request,
    limit: int = 100,
    decision: str | None = None,
    user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
) -> list[AuditOut]:
    limit = max(1, min(limit, 1000))
    query = db.query(AuditLog).order_by(AuditLog.id.desc())
    if decision in ("allow", "deny"):
        query = query.filter(AuditLog.decision == decision)
    rows = query.limit(limit).all()
    log_event(db, actor=user.username, role=user.role, action="audit_view", resource=f"limit={limit}", decision="allow", ip=client_ip(request))
    return [AuditOut.model_validate(row) for row in rows]


@router.get("/users", response_model=list[UserAdminOut])
def users_list(
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserAdminOut]:
    rows = db.query(User).order_by(User.username).all()
    log_event(db, actor=user.username, role=user.role, action="users_view", resource="all", decision="allow", ip=client_ip(request))
    return [
        UserAdminOut(
            username=row.username,
            full_name=row.full_name,
            role=row.role,
            is_active=row.is_active,
            failed_attempts=row.failed_attempts,
            locked_until=row.locked_until,
            last_login_at=row.last_login_at,
        )
        for row in rows
    ]
