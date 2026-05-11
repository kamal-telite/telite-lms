from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.services.email import send_password_reset_email
from app.services.store import (
    create_session,
    create_password_reset_token,
    fetch_user_by_id,
    fetch_user_by_identifier,
    get_session_by_token,
    is_admin_role,
    is_tenant_super_admin_role,
    reset_password_with_token,
    revoke_session,
    update_last_login,
    verify_password,
)


ACCESS_TOKEN_HOURS = int(os.getenv("TELITE_ACCESS_TOKEN_HOURS", "8"))
REFRESH_TOKEN_DAYS = int(os.getenv("TELITE_REFRESH_TOKEN_DAYS", "14"))
AUTH_SECRET = os.getenv("TELITE_AUTH_SECRET", "telite-local-dev-secret")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(value: str) -> str:
    return hmac.new(AUTH_SECRET.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_token(payload: dict[str, Any]) -> str:
    encoded = _b64_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{encoded}.{_sign(encoded)}"


def _decode_token(token: str) -> dict[str, Any]:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token format") from exc
    expected = _sign(encoded)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid token signature")
    payload = json.loads(_b64_decode(encoded))
    exp = payload.get("exp")
    if exp is None or datetime.now(timezone.utc).timestamp() > exp:
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def _access_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["full_name"],
        "category_scope": user["category_scope"],
        "org_id": user.get("org_id"),
        "is_platform_admin": bool(user.get("is_platform_admin")),
        "type": "access",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_HOURS)).timestamp(),
    }


def _refresh_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "sub": user["id"],
        "type": "refresh",
        "exp": (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)).timestamp(),
    }


class TokenData(BaseModel):
    id: str
    email: str
    role: str
    full_name: str
    category_scope: str | None = None
    org_id: int | None = None
    is_platform_admin: bool = False


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


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


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


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = fetch_user_by_id(payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")
    return TokenData(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        full_name=user["full_name"],
        category_scope=user["category_scope"],
        org_id=user.get("org_id"),
        is_platform_admin=bool(user.get("is_platform_admin")),
    )


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


def _token_response(user: dict[str, Any], refresh_token: str) -> TokenResponse:
    access_token = _build_token(_access_payload(user))
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
    )


def issue_login_response(user: dict[str, Any]) -> TokenResponse:
    refresh_token = _build_token(_refresh_payload(user))
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    ).strftime("%Y-%m-%d %H:%M")
    create_session(user["id"], refresh_token, expires_at)
    update_last_login(user["id"])
    return _token_response(user, refresh_token)


@auth_router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = authenticate_user(form_data.username, form_data.password)
    return issue_login_response(user)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest) -> TokenResponse:
    payload = _decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session = get_session_by_token(body.refresh_token)
    if not session:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    user = fetch_user_by_id(payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")
    return _token_response(user, body.refresh_token)


@auth_router.post("/logout")
def logout(
    body: LogoutRequest,
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, str]:
    if body.refresh_token:
        revoke_session(body.refresh_token)
    return {"status": "logged_out", "user_id": current_user.id}


@auth_router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest) -> dict[str, str]:
    reset_request = create_password_reset_token(body.email)
    if reset_request:
        send_password_reset_email(
            to_email=reset_request["email"],
            name=reset_request["full_name"],
            token=reset_request["token"],
            expires_at=reset_request["expires_at"],
        )
    return {
        "status": "ok",
        "message": "If an account exists for that email, a password reset link has been sent.",
    }


@auth_router.post("/reset-password")
def reset_password(body: ResetPasswordRequest) -> dict[str, str]:
    try:
        user = reset_password_with_token(body.token, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    }
