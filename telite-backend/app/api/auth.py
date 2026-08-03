"""
Authentication module for Telite LMS.

PHASE 2 SECURITY HARDENING:
- PyJWT replaces custom base64+HMAC implementation
- HttpOnly Secure cookies replace localStorage JWT storage
- CSRF double-submit cookie protection on all mutations
- Redis-backed distributed rate limiting
- Production secret validation (fails hard if not set)
- Refresh token stored in DB and revocable
- No hardcoded secrets or fallback values in production
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    username: str | None = None
    avatar: str | None = None

class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_access_payload,
    create_refresh_payload,
    decode_token,
    generate_csrf_token,
    validate_csrf_token,
)
from app.core.rate_limiter import clear_attempts, is_limited, record_attempt
from app.core.request_context import set_org_id, set_user_id
from app.services.email import send_password_reset_email
from app.core.password_utils import verify_password
from sqlalchemy import or_, select, update, text
from sqlalchemy.orm import Session

from app.db.rls import set_rls_context, set_platform_context, clear_rls_context
from app.db.engine import db_session, is_postgres_dsn
from app.models.user import User
from app.models.membership import Membership
from app.repositories.user_repo import UserRepository, fetch_user_by_id
from app.repositories.auth_repo import AuthRepository

# ── Configuration ─────────────────────────────────────────────────────────────

LOGIN_FAILURE_LIMIT = int(os.getenv("TELITE_LOGIN_FAILURE_LIMIT", "5"))
LOGIN_FAILURE_WINDOW_SECONDS = int(os.getenv("TELITE_LOGIN_FAILURE_WINDOW_SECONDS", "300"))
FORGOT_PASSWORD_LIMIT = int(os.getenv("TELITE_FORGOT_PASSWORD_LIMIT", "3"))
FORGOT_PASSWORD_WINDOW_SECONDS = int(os.getenv("TELITE_FORGOT_PASSWORD_WINDOW_SECONDS", "900"))
RESET_PASSWORD_LIMIT = int(os.getenv("TELITE_RESET_PASSWORD_LIMIT", "5"))
RESET_PASSWORD_WINDOW_SECONDS = int(os.getenv("TELITE_RESET_PASSWORD_WINDOW_SECONDS", "900"))
REFRESH_TOKEN_DAYS = int(os.getenv("TELITE_REFRESH_TOKEN_DAYS", "14"))
THEME_PREFERENCES = {"light", "dark", "system"}

# Cookie settings — tighten in production
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")   # "strict" in production
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "") or None   # e.g. ".telite.com"
COOKIE_HTTPONLY = True                                    # always HttpOnly

# Bearer fallback for API clients / Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _client_user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "unknown")[:500]


def _account_refresh_cookie_name(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:20]
    return f"telite_account_refresh_{digest}"


def _rate_key(namespace: str, raw_value: str) -> str:
    normalized = raw_value.strip().lower() or "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def _raise_rate_limit(retry_after: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later.",
        headers={"Retry-After": str(retry_after)},
    )


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    *,
    account_user_id: str | None = None,
) -> None:
    """Set HttpOnly auth cookies and a readable CSRF cookie."""
    access_max_age = int(os.getenv("TELITE_ACCESS_TOKEN_HOURS", "8")) * 3600
    refresh_max_age = REFRESH_TOKEN_DAYS * 86400

    # Access token — HttpOnly, not readable by JS
    response.set_cookie(
        key="telite_access_token",
        value=access_token,
        max_age=access_max_age,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )
    # Refresh token — HttpOnly, only sent to /auth/refresh
    response.set_cookie(
        key="telite_refresh_token",
        value=refresh_token,
        max_age=refresh_max_age,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/auth/refresh",
    )
    if account_user_id and refresh_token:
        response.set_cookie(
            key=_account_refresh_cookie_name(account_user_id),
            value=refresh_token,
            max_age=refresh_max_age,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path="/auth/sessions/switch-account",
        )
    # CSRF token — NOT HttpOnly so JS can read and send it in X-CSRF-Token header
    response.set_cookie(
        key="telite_csrf_token",
        value=csrf_token,
        max_age=access_max_age,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies on logout."""
    for name, path in [
        ("telite_access_token", "/"),
        ("telite_refresh_token", "/auth/refresh"),
        ("telite_csrf_token", "/"),
    ]:
        response.delete_cookie(
            key=name,
            path=path,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
        )


# ── Pydantic models ───────────────────────────────────────────────────────────

class TokenData(BaseModel):
    """
    Decoded JWT payload attached to every authenticated request.
    Phase 4: includes permissions list for fast frontend checks.
    """
    id: str
    username: str | None = None
    email: str
    role: str
    full_name: str
    category_scope: str | None = None
    org_id: int | None = None
    is_platform_admin: bool = False
    permissions: list[str] = []
    theme_preference: str = "system"

    def has_permission(self, permission: str) -> bool:
        """Fast permission check without DB lookup."""
        if self.is_platform_admin:
            return True
        return permission in self.permissions


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str | None = None
    role: str
    name: str
    email: str
    category_scope: str | None = None
    org_id: int | None = None
    is_platform_admin: bool = False
    permissions: list[str] = []
    theme_preference: str = "system"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None   # optional — cookie is preferred


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ThemePreferenceRequest(BaseModel):
    theme_preference: str


# ── Core auth functions ───────────────────────────────────────────────────────

def authenticate_user(db: Session, identifier: str, password: str):
    from app.repositories.user_repo import UserRepository, IdentifierCollisionError
    repo = UserRepository(db)
    try:
        user = repo.get_by_identifier_for_auth(identifier)
    except IdentifierCollisionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias="telite_access_token"),
    db: Session = Depends(db_session),
) -> TokenData:
    """
    Resolve the current user from either:
    1. HttpOnly cookie (preferred — browser clients)
    2. Bearer token header (API clients / Swagger)

    Phase 4: permissions list populated from JWT claims.
    """
    bearer = bearer_token.strip() if bearer_token else None
    if bearer and bearer.lower() in {"null", "undefined", "none"}:
        bearer = None

    token = bearer or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token, token_type="access")
    
    org_id = payload.get("org_id")
    is_platform_admin = payload.get("is_platform_admin", False)
    
    if org_id is not None:
        set_rls_context(db, org_id)
    elif is_platform_admin:
        set_platform_context(db)
    else:
        raise HTTPException(status_code=401, detail="Invalid token payload: no tenant context")

    repo = UserRepository(db)
    user = repo.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or not found")

    # Set logging context for observability
    set_user_id(user.id)
    set_org_id(user.org_id)

    return TokenData(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        category_scope=user.category_scope,
        org_id=user.org_id,
        is_platform_admin=bool(payload.get("is_platform_admin", user.is_platform_admin)),
        permissions=payload.get("permissions", []),
        theme_preference=user.theme_preference or "system",
    )


def validate_csrf(
    request: Request,
    csrf_cookie: str | None = Cookie(default=None, alias="telite_csrf_token"),
) -> None:
    """
    CSRF double-submit cookie validation.
    Skipped for GET/HEAD/OPTIONS (safe methods).
    Skipped for Bearer-only clients (no CSRF cookie present).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # If no CSRF cookie, client is using Bearer auth — skip CSRF check
    if not csrf_cookie:
        return

    header_token = request.headers.get("X-CSRF-Token", "")
    if not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header.",
        )

    if not validate_csrf_token(header_token, csrf_cookie):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid.",
        )


# ── Role guards ───────────────────────────────────────────────────────────────

def is_admin_role(role: str) -> bool:
    return role in ("super_admin", "category_admin", "platform_admin")

def is_tenant_super_admin_role(role: str) -> bool:
    return role == "super_admin"


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if not current_user.is_platform_admin and not is_admin_role(current_user.role):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_super_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if not current_user.is_platform_admin and not is_tenant_super_admin_role(current_user.role):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


def require_platform_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return current_user


def resolve_org_scope(current_user: TokenData, requested_org_id: int | None = None) -> int | None:
    if current_user.is_platform_admin:
        return requested_org_id if requested_org_id is not None else current_user.org_id
    if current_user.org_id is None:
        raise HTTPException(status_code=403, detail="Organization context is required")
    if requested_org_id is not None and requested_org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="You do not have access to this organization")
    return current_user.org_id


def ensure_org_access(current_user: TokenData, target_org_id: int | None) -> int | None:
    if current_user.is_platform_admin:
        return target_org_id
    if current_user.org_id is None or target_org_id is None or current_user.org_id != target_org_id:
        raise HTTPException(status_code=403, detail="You do not have access to this organization")
    return target_org_id


# ── Internal logic ─────────────────────────────────────────────────────────────

def _build_token_response(user: dict[str, Any], refresh_token: str, db: Session | None = None) -> TokenResponse:
    from app.core.permissions import resolve_permissions
    access_token = create_access_token(create_access_payload(user, db))
    permissions = resolve_permissions(
        role=user["role"],
        is_platform_admin=bool(user.get("is_platform_admin")),
        category_scope=user.get("category_scope"),
        org_id=user.get("org_id"),
        db=db,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user["id"],
        username=user.get("username"),
        role=user["role"],
        name=user["full_name"],
        email=user["email"],
        category_scope=user.get("category_scope"),
        org_id=user.get("org_id"),
        is_platform_admin=bool(user.get("is_platform_admin")),
        permissions=permissions,
        theme_preference=user.get("theme_preference") or "system",
    )


def issue_login_response(
    db: Session,
    user,
    response: Response,
    request: Request | None = None,
) -> TokenResponse:
    """Issue tokens, persist session, set cookies, return response body."""
    resolved_role = user.role
    resolved_category_scope = user.category_scope
    resolved_org_id = user.org_id

    if not user.is_platform_admin and user.org_id is not None:
        try:
            if is_postgres_dsn():
                db.execute(text("SET LOCAL app.bypass_rls = 'on'"))
            membership = db.execute(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.org_id == user.org_id,
                    Membership.status == "active",
                )
            ).scalar_one_or_none()
            if membership:
                resolved_role = membership.role
                resolved_category_scope = membership.category_scope
                resolved_org_id = membership.org_id
        finally:
            if is_postgres_dsn():
                db.execute(text("SET LOCAL app.bypass_rls = 'off'"))

    user_dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": resolved_role,
        "full_name": user.full_name,
        "category_scope": resolved_category_scope,
        "org_id": resolved_org_id,
        "is_platform_admin": user.is_platform_admin,
        "theme_preference": user.theme_preference or "system",
    }
    refresh_token = create_refresh_token(create_refresh_payload(user_dict))
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    ).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        set_rls_context(db, user.org_id)

        auth_repo = AuthRepository(db)
        auth_repo.create_session(
            user_id=user.id,
            org_id=user.org_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        
        user_repo = UserRepository(db)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        user_repo.update_last_login(user.id, now_str)
    finally:
        clear_rls_context(db)

    token_response = _build_token_response(user_dict, refresh_token, db=db)
    csrf_token = generate_csrf_token()


    # Set HttpOnly cookies
    _set_auth_cookies(
        response,
        token_response.access_token,
        refresh_token,
        csrf_token,
        account_user_id=user.id,
    )

    return token_response

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(db_session),
) -> TokenResponse:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-login-ip", client_ip)
    identifier_key = _rate_key("auth-login-identifier", form_data.username)

    for key in (ip_key, identifier_key):
        retry_after = is_limited(key, limit=LOGIN_FAILURE_LIMIT, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        if retry_after is not None:
            _raise_rate_limit(retry_after)

    try:
        user = authenticate_user(db, form_data.username, form_data.password)
    except HTTPException:
        record_attempt(ip_key, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        record_attempt(identifier_key, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        raise

    clear_attempts(ip_key)
    clear_attempts(identifier_key)
    return issue_login_response(db, user, response, request)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    body: RefreshRequest | None = None,
    cookie_refresh: str | None = Cookie(default=None, alias="telite_refresh_token"),
    db: Session = Depends(db_session),
) -> TokenResponse:
    refresh_token = cookie_refresh or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    payload = decode_token(refresh_token, token_type="refresh")

    from app.repositories.auth_repo import AuthRepository
    from app.repositories.user_repo import UserRepository
    from app.db.rls import set_rls_context
    from sqlalchemy import text

    org_id = payload.get("org_id")
    is_platform_admin = payload.get("is_platform_admin", False)

    try:
        if org_id is not None:
            set_rls_context(db, org_id)
        elif is_platform_admin:
            set_platform_context(db)
        else:
            raise HTTPException(status_code=401, detail="Invalid token payload: no tenant context")

        auth_repo = AuthRepository(db)
        session = auth_repo.get_by_token(refresh_token)
        if not session:
            raise HTTPException(status_code=401, detail="Refresh token has been revoked or not found")

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User is inactive")

        return issue_login_response(db, user, response)

    finally:
        clear_rls_context(db)


@auth_router.post("/logout")
def logout(
    response: Response,
    body: LogoutRequest | None = None,
    current_user: TokenData = Depends(get_current_user),
    cookie_refresh: str | None = Cookie(default=None, alias="telite_refresh_token"),
    db: Session = Depends(db_session),
) -> dict[str, str]:
    refresh_token = cookie_refresh or (body.refresh_token if body else None)
    if refresh_token:
        from app.repositories.auth_repo import AuthRepository
        from app.db.rls import set_rls_context
        from sqlalchemy import text
        try:
            if current_user.org_id is not None:
                set_rls_context(db, current_user.org_id)
            elif current_user.is_platform_admin:
                set_platform_context(db)
                
            AuthRepository(db).revoke_session(refresh_token)
        finally:
            clear_rls_context(db)

    _clear_auth_cookies(response)
    return {"status": "ok"}


@auth_router.patch("/me")
def update_profile(
    body: UpdateProfileRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.repositories.user_repo import UserRepository, IdentifierCollisionError
    from app.repositories.audit_repo import AuditRepository
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = body.model_dump(exclude_unset=True)
    
    # Check uniqueness if email or username is updated
    new_email = update_data.get("email", user.email)
    new_username = update_data.get("username", user.username)
    
    if "email" in update_data or "username" in update_data:
        try:
            user_repo.validate_identifier_uniqueness(new_email, new_username, exclude_user_id=user.id)
        except IdentifierCollisionError as e:
            raise HTTPException(status_code=409, detail=str(e))
            
    if "full_name" in update_data:
        user.full_name = update_data["full_name"]
    if "email" in update_data:
        user.email = new_email.strip().lower()
    if "username" in update_data:
        user.username = new_username.strip().lower()
    if "avatar" in update_data:
        user.avatar_initials = update_data["avatar"]
    
    db.commit()

    AuditRepository(db).write(
        org_id=user.org_id,
        actor_user_id=user.id,
        actor_name=user.full_name,
        action="user.update_profile",
        target_type="user",
        target_id=user.id,
        message="Updated profile settings",
    )
    
    return {"status": "ok", "user": user.to_dict()}


@auth_router.post("/me/password")
def update_password(
    body: UpdatePasswordRequest,
    response: Response,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.repositories.user_repo import UserRepository
    from app.repositories.auth_repo import AuthRepository
    from app.repositories.audit_repo import AuditRepository
    from app.core.password_utils import verify_password, hash_password, validate_password_strength
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    is_valid, error_msg = validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
        
    user.password_hash = hash_password(body.new_password)
    db.commit()

    # Revoke all sessions, forcing re-login after password change
    auth_repo = AuthRepository(db)
    auth_repo.revoke_all_for_user(user.id)
    _clear_auth_cookies(response)

    AuditRepository(db).write(
        org_id=user.org_id,
        actor_user_id=user.id,
        actor_name=user.full_name,
        action="user.update_password",
        target_type="user",
        target_id=user.id,
        message="Updated account password",
    )
    
    return {"status": "ok", "message": "Password updated successfully. Please log in again."}


@auth_router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest, 
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-forgot-password-ip", client_ip)
    email_key = _rate_key("auth-forgot-password-email", body.email)

    for key in (ip_key, email_key):
        retry_after = is_limited(key, limit=FORGOT_PASSWORD_LIMIT, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)
        if retry_after is not None:
            _raise_rate_limit(retry_after)

    record_attempt(ip_key, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)
    record_attempt(email_key, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)

    from app.repositories.user_repo import UserRepository
    from app.repositories.auth_repo import AuthRepository
    from sqlalchemy import text
    try:
        set_platform_context(db)
        user_repo = UserRepository(db)
        user = user_repo.get_by_email(body.email)
        
        if user and user.is_active:
            auth_repo = AuthRepository(db)
            reset_record = auth_repo.create_password_reset_token(user.id)
            send_password_reset_email(
                to_email=user.email,
                name=user.full_name,
                token=reset_record.token,
                expires_at=reset_record.expires_at,
            )
    finally:
        clear_rls_context(db)

    # Always return the same message to prevent email enumeration
    return {
        "status": "ok",
        "message": "If an account exists for that email, a password reset link has been sent.",
    }


@auth_router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest, 
    request: Request,
    db: Session = Depends(db_session),
) -> dict[str, str]:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-reset-password-ip", client_ip)

    retry_after = is_limited(ip_key, limit=RESET_PASSWORD_LIMIT, window_seconds=RESET_PASSWORD_WINDOW_SECONDS)
    if retry_after is not None:
        _raise_rate_limit(retry_after)

    record_attempt(ip_key, window_seconds=RESET_PASSWORD_WINDOW_SECONDS)

    from app.repositories.auth_repo import AuthRepository
    from app.repositories.user_repo import UserRepository
    from sqlalchemy import text
    import datetime
    
    try:
        set_platform_context(db)
        auth_repo = AuthRepository(db)
        token_record = auth_repo.get_password_reset_token(body.token)
        
        if not token_record or token_record.used_at is not None:
            raise ValueError("Invalid or expired reset token.")
            
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if token_record.expires_at < now:
            raise ValueError("Reset token has expired.")
            
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise ValueError("Invalid user state.")
            
        auth_repo.mark_password_reset_token_used(token_record.id)
        user_repo.update_password(user, body.password)
        auth_repo.revoke_all_for_user(user.id)
        user_id = user.id
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        clear_rls_context(db)

    clear_attempts(ip_key)
    return {"status": "password_updated", "user_id": user_id}


@auth_router.get("/me")
def get_me(current_user: TokenData = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.full_name,
        "role": current_user.role,
        "category_scope": current_user.category_scope,
        "org_id": current_user.org_id,
        "is_platform_admin": current_user.is_platform_admin,
        "is_active": True,
        "permissions": current_user.permissions,
        "theme_preference": current_user.theme_preference,
    }


@auth_router.patch("/preferences/theme")
def update_theme_preference(
    body: ThemePreferenceRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict[str, str]:
    theme_preference = body.theme_preference.strip().lower()
    if theme_preference not in THEME_PREFERENCES:
        raise HTTPException(
            status_code=400,
            detail="theme_preference must be one of: light, dark, system",
        )

    UserRepository(db).update_theme_preference(current_user.id, theme_preference)
    db.commit()
    return {
        "user_id": current_user.id,
        "theme_preference": theme_preference,
    }
