from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..audit import log_event
from ..config import get_settings
from ..db import get_db
from ..models import User, utcnow
from ..schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from ..security import client_ip, create_access_token, get_current_user, hash_password, rate_limiter, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _authenticate(payload: LoginRequest, request: Request, db: Session) -> TokenResponse:
    ip = client_ip(request)
    username = payload.username.strip().lower()

    allowed, retry_after = rate_limiter.check(f"login:{ip}", settings.rate_limit_login_per_minute)
    if not allowed:
        log_event(db, actor=username, action="login_rate_limited", decision="deny", detail=f"retry after {retry_after}s", ip=ip)
        raise HTTPException(429, f"Too many login attempts. Try again in {retry_after} seconds.", headers={"Retry-After": str(retry_after)})

    user = db.query(User).filter(User.username == username).first()
    now = utcnow()

    if user and user.locked_until and user.locked_until > now:
        minutes = int((user.locked_until - now).total_seconds() // 60) + 1
        log_event(db, actor=user.username, role=user.role, action="login_locked", decision="deny", detail="attempt on locked account", ip=ip)
        raise HTTPException(423, f"Account locked after too many failed attempts. Try again in about {minutes} minute(s).")

    # lockout window elapsed -> reset the counter
    if user and user.locked_until and user.locked_until <= now:
        user.failed_attempts = 0
        user.locked_until = None
        db.commit()

    if user and user.is_active and verify_password(user.password_hash, payload.password):
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        db.commit()
        log_event(db, actor=user.username, role=user.role, action="login_success", ip=ip)
        return TokenResponse(
            access_token=create_access_token(user),
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )

    if user and user.is_active:
        user.failed_attempts += 1
        if user.failed_attempts >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            db.commit()
            log_event(db, actor=user.username, role=user.role, action="account_locked", decision="deny", detail=f"{user.failed_attempts} failed attempts; locked for {settings.login_lockout_minutes} min", ip=ip)
            raise HTTPException(423, f"Account locked for {settings.login_lockout_minutes} minutes after {settings.login_max_attempts} failed attempts.")
        remaining = settings.login_max_attempts - user.failed_attempts
        db.commit()
        log_event(db, actor=user.username, role=user.role, action="login_failed", decision="deny", detail=f"failed attempt {user.failed_attempts}/{settings.login_max_attempts}", ip=ip)
        message = "Invalid username or password."
        if remaining <= 2:
            message += f" {remaining} attempt(s) left before lockout."
        raise HTTPException(401, message)

    log_event(db, actor=username, action="login_failed", decision="deny", detail="unknown or inactive user", ip=ip)
    raise HTTPException(401, "Invalid username or password.")


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)) -> UserOut:
    """Create a new account with a chosen role. Sign in afterwards with the same password."""
    ip = client_ip(request)
    username = payload.username.strip().lower()

    allowed, retry_after = rate_limiter.check(f"signup:{ip}", settings.rate_limit_login_per_minute)
    if not allowed:
        log_event(db, actor=username, action="signup_rate_limited", decision="deny", detail=f"retry after {retry_after}s", ip=ip)
        raise HTTPException(429, f"Too many sign-up attempts. Try again in {retry_after} seconds.", headers={"Retry-After": str(retry_after)})

    if db.query(User).filter(User.username == username).first():
        log_event(db, actor=username, action="signup_denied", decision="deny", detail="username already taken", ip=ip)
        raise HTTPException(409, "That username is already taken. Please choose another one.")

    user = User(
        username=username,
        full_name=payload.full_name.strip(),
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_event(db, actor=user.username, role=user.role, action="signup_success", detail=f"account created (role: {user.role})", ip=ip)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """JSON login -> JWT access token."""
    return _authenticate(payload, request, db)


@router.post("/token", response_model=TokenResponse)
def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 password flow (used by the Swagger UI Authorize button)."""
    return _authenticate(LoginRequest(username=form_data.username, password=form_data.password), request, db)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    """Current identity, derived solely from the verified token."""
    return UserOut.model_validate(user)


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    log_event(db, actor=user.username, role=user.role, action="logout", ip=client_ip(request))
    return {"detail": "Logged out. Discard the token on the client."}
