from sqlalchemy.orm import Session

from .models import AuditLog, utcnow


def log_event(
    db: Session,
    *,
    actor: str,
    action: str,
    role: str = "-",
    resource: str = "",
    decision: str = "allow",
    detail: str = "",
    ip: str = "",
) -> None:
    """Append an entry to the audit log. Commits immediately so entries are
    persisted even if the request later fails."""
    db.add(
        AuditLog(
            ts=utcnow(),
            actor=actor,
            role=role,
            action=action,
            resource=resource[:128],
            decision=decision,
            detail=detail[:2000],
            ip=ip[:64],
        )
    )
    db.commit()
