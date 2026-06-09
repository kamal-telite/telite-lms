"""
Security utilities for Telite LMS.

This module provides secure JWT token generation and validation using PyJWT,
replacing the custom JWT implementation with industry-standard practices.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status


# JWT Configuration
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_HOURS = int(os.getenv("TELITE_ACCESS_TOKEN_HOURS", "8"))
REFRESH_TOKEN_DAYS = int(os.getenv("TELITE_REFRESH_TOKEN_DAYS", "14"))

# CRITICAL: Secret must be set in production
AUTH_SECRET = os.getenv("TELITE_AUTH_SECRET", "")

# Validate secret in production
if not AUTH_SECRET:
    # Check if we're in a production-like environment
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env in ("production", "prod", "staging"):
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: TELITE_AUTH_SECRET must be set in production. "
            "Generate a secure secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    # Development fallback with clear warning
    AUTH_SECRET = "INSECURE-DEV-SECRET-DO-NOT-USE-IN-PRODUCTION"
    print("WARNING: Using insecure development secret. Set TELITE_AUTH_SECRET for production!")


def generate_secure_secret() -> str:
    """Generate a cryptographically secure secret for JWT signing."""
    return secrets.token_urlsafe(32)


def create_access_token(payload: dict[str, Any]) -> str:
    """
    Create a JWT access token using PyJWT.
    
    Args:
        payload: Token payload containing user information
        
    Returns:
        Encoded JWT token string
        
    Raises:
        RuntimeError: If AUTH_SECRET is not configured
    """
    if not AUTH_SECRET or AUTH_SECRET == "INSECURE-DEV-SECRET-DO-NOT-USE-IN-PRODUCTION":
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod", "staging"):
            raise RuntimeError("Cannot create tokens without secure AUTH_SECRET in production")
    
    # Add standard JWT claims
    now = datetime.now(timezone.utc)
    token_payload = {
        **payload,
        "iat": now,  # Issued at
        "exp": now + timedelta(hours=ACCESS_TOKEN_HOURS),  # Expiration
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    
    return jwt.encode(token_payload, AUTH_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(payload: dict[str, Any]) -> str:
    """
    Create a JWT refresh token using PyJWT.
    
    Args:
        payload: Token payload containing user ID
        
    Returns:
        Encoded JWT token string
    """
    if not AUTH_SECRET or AUTH_SECRET == "INSECURE-DEV-SECRET-DO-NOT-USE-IN-PRODUCTION":
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod", "staging"):
            raise RuntimeError("Cannot create tokens without secure AUTH_SECRET in production")
    
    now = datetime.now(timezone.utc)
    token_payload = {
        **payload,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_DAYS),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    
    return jwt.encode(token_payload, AUTH_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """
    Decode and validate a JWT token using PyJWT.
    
    Args:
        token: JWT token string to decode
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            AUTH_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "iat", "type"],
            }
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
        
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def create_access_payload(user: dict[str, Any]) -> dict[str, Any]:
    """
    Create the payload for an access token.
    Phase 4: includes full permissions list in JWT.
    """
    from app.core.permissions import build_jwt_claims
    return build_jwt_claims(user)


def create_refresh_payload(user: dict[str, Any]) -> dict[str, Any]:
    """
    Create the payload for a refresh token.
    Minimal payload — only user ID needed.
    """
    return {
        "sub": user["id"],
        "org_id": user.get("org_id") or user.get("organization_id"),
    }


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """
    Validate a CSRF token using constant-time comparison.
    
    Args:
        token: Token from request
        expected: Expected token value
        
    Returns:
        True if tokens match, False otherwise
    """
    return secrets.compare_digest(token, expected)
