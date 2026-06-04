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
from app.services.email import send_password_reset_email
from app.services.store import (
    create_session,
    create_password_reset_token,
    fetch_user_by_id,
    fetch_user_by_identifier,
    get_session_by_token,
    is_admin_role,
    is_tenant_super_admin_role,
    record_password_reset_delivery,
    reset_password_with_token,
    revoke_session,
    update_last_login,
    verify_password,
)

# ── Configuration ─────────────────────────────────────────────────────────────

LOGIN_FAILURE_LIMIT = int(os.getenv("TELITE_LOGIN_FAILURE_LIMIT", "5"))
LOGIN_FAILURE_WINDOW_SECONDS = int(os.getenv("TELITE_LOGIN_FAILURE_WINDOW_SECONDS", "300"))
FORGOT_PASSWORD_LIMIT = int(os.getenv("TELITE_FORGOT_PASSWORD_LIMIT", "3"))
FORGOT_PASSWORD_WINDOW_SECONDS = int(os.getenv("TELITE_FORGOT_PASSWORD_WINDOW_SECONDS", "900"))
RESET_PASSWORD_LIMIT = int(os.getenv("TELITE_RESET_PASSWORD_LIMIT", "5"))
RESET_PASSWORD_WINDOW_SECONDS = int(os.getenv("TELITE_RESET_PASSWORD_WINDOW_SECONDS", "900"))
REFRESH_TOKEN_DAYS = int(os.getenv("TELITE_REFRESH_TOKEN_DAYS", "14"))

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
    email: str
    role: str
    full_name: str
    category_scope: str | None = None
    org_id: int | None = None
    is_platform_admin: bool = False
    permissions: list[str] = []

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
    role: str
    name: str
    email: str
    category_scope: str | None = None
    org_id: int | None = None
    is_platform_admin: bool = False
    permissions: list[str] = []


class RefreshRequest(BaseModel):
    refresh_token: str | None = None   # optional — cookie is preferred


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# ── Core auth functions ───────────────────────────────────────────────────────

def authenticate_user(identifier: str, password: str) -> dict[str, Any]:
    user = fetch_user_by_identifier(identifier, include_secret=True)
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user["password_hash"]):
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
) -> TokenData:
    """
    Resolve the current user from either:
    1. HttpOnly cookie (preferred — browser clients)
    2. Bearer token header (API clients / Swagger)

    Phase 4: permissions list populated from JWT claims.
    """
    token = cookie_token or bearer_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token, token_type="access")
    user = fetch_user_by_id(payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive or not found")

    return TokenData(
        id=user["id"],
        email=payload.get("email") or user["email"],
        role=payload.get("role") or user["role"],
        full_name=payload.get("name") or user["full_name"],
        category_scope=payload.get("category_scope", user["category_scope"]),
        org_id=payload.get("org_id", user.get("org_id")),
        is_platform_admin=bool(payload.get("is_platform_admin", user.get("is_platform_admin"))),
        permissions=payload.get("permissions", []),
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


# ── Token helpers ─────────────────────────────────────────────────────────────

def _build_token_response(user: dict[str, Any], refresh_token: str) -> TokenResponse:
    from app.core.permissions import resolve_permissions
    access_token = create_access_token(create_access_payload(user))
    permissions = resolve_permissions(
        user["role"],
        bool(user.get("is_platform_admin")),
        user.get("category_scope"),
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user["id"],
        role=user["role"],
        name=user["full_name"],
        email=user["email"],
        category_scope=user["category_scope"],
        org_id=user.get("org_id"),
        is_platform_admin=bool(user.get("is_platform_admin")),
        permissions=permissions,
    )


def issue_login_response(
    user: dict[str, Any],
    response: Response,
    request: Request | None = None,
) -> TokenResponse:
    """Issue tokens, persist session, set cookies, return response body."""
    refresh_token = create_refresh_token(create_refresh_payload(user))
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    ).strftime("%Y-%m-%d %H:%M")
    create_session(
        user["id"],
        refresh_token,
        expires_at,
        org_id=user.get("org_id") or user.get("organization_id"),
        user_agent=_client_user_agent(request) if request else None,
        ip_address=_client_ip(request) if request else None,
    )
    update_last_login(user["id"])

    token_response = _build_token_response(user, refresh_token)
    csrf_token = generate_csrf_token()

    # Set HttpOnly cookies
    _set_auth_cookies(
        response,
        token_response.access_token,
        refresh_token,
        csrf_token,
        account_user_id=user["id"],
    )

    return token_response


# ── Router ────────────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-login-ip", client_ip)
    identifier_key = _rate_key("auth-login-identifier", form_data.username)

    for key in (ip_key, identifier_key):
        retry_after = is_limited(key, limit=LOGIN_FAILURE_LIMIT, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        if retry_after is not None:
            _raise_rate_limit(retry_after)

    try:
        user = authenticate_user(form_data.username, form_data.password)
    except HTTPException:
        record_attempt(ip_key, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        record_attempt(identifier_key, window_seconds=LOGIN_FAILURE_WINDOW_SECONDS)
        raise

    clear_attempts(ip_key)
    clear_attempts(identifier_key)
    return issue_login_response(user, response, request)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    body: RefreshRequest | None = None,
    cookie_refresh: str | None = Cookie(default=None, alias="telite_refresh_token"),
) -> TokenResponse:
    # Prefer cookie, fall back to body
    refresh_token = cookie_refresh or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    payload = decode_token(refresh_token, token_type="refresh")
    session = get_session_by_token(refresh_token)
    if not session:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user = fetch_user_by_id(payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")

    session_org_id = session.get("org_id") or payload.get("org_id")
    if session_org_id is not None:
        user = dict(user)
        user["org_id"] = session_org_id
        user["organization_id"] = session_org_id

    token_response = _build_token_response(user, refresh_token)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(
        response,
        token_response.access_token,
        refresh_token,
        csrf_token,
        account_user_id=user["id"],
    )
    return token_response


@auth_router.post("/logout")
def logout(
    response: Response,
    body: LogoutRequest | None = None,
    current_user: TokenData = Depends(get_current_user),
    cookie_refresh: str | None = Cookie(default=None, alias="telite_refresh_token"),
) -> dict[str, str]:
    refresh_token = cookie_refresh or (body.refresh_token if body else None)
    if refresh_token:
        revoke_session(refresh_token)
    _clear_auth_cookies(response)
    return {"status": "logged_out", "user_id": current_user.id}


@auth_router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request) -> dict[str, str]:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-forgot-password-ip", client_ip)
    email_key = _rate_key("auth-forgot-password-email", body.email)

    for key in (ip_key, email_key):
        retry_after = is_limited(key, limit=FORGOT_PASSWORD_LIMIT, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)
        if retry_after is not None:
            _raise_rate_limit(retry_after)

    record_attempt(ip_key, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)
    record_attempt(email_key, window_seconds=FORGOT_PASSWORD_WINDOW_SECONDS)

    reset_request = create_password_reset_token(body.email)
    if reset_request:
        delivered = send_password_reset_email(
            to_email=reset_request["email"],
            name=reset_request["full_name"],
            token=reset_request["token"],
            expires_at=reset_request["expires_at"],
        )
        if reset_request.get("id") is not None:
            record_password_reset_delivery(
                reset_request["id"],
                delivered=delivered,
                error=None if delivered else "SMTP not configured or delivery failed",
            )

    # Always return the same message to prevent email enumeration
    return {
        "status": "ok",
        "message": "If an account exists for that email, a password reset link has been sent.",
    }


@auth_router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request) -> dict[str, str]:
    client_ip = _client_ip(request)
    ip_key = _rate_key("auth-reset-password-ip", client_ip)

    retry_after = is_limited(ip_key, limit=RESET_PASSWORD_LIMIT, window_seconds=RESET_PASSWORD_WINDOW_SECONDS)
    if retry_after is not None:
        _raise_rate_limit(retry_after)

    record_attempt(ip_key, window_seconds=RESET_PASSWORD_WINDOW_SECONDS)

    try:
        user = reset_password_with_token(body.token, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    clear_attempts(ip_key)
    return {"status": "password_updated", "user_id": user["id"]}


@auth_router.get("/me")
def get_me(current_user: TokenData = Depends(get_current_user)) -> dict[str, Any]:
    user = fetch_user_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "name": user["full_name"],
        "role": user["role"],
        "category_scope": user["category_scope"],
        "org_id": user.get("org_id"),
        "is_platform_admin": bool(user.get("is_platform_admin")),
        "is_active": user["is_active"],
        "permissions": current_user.permissions,
    }
