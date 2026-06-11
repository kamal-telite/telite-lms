"""
Secure password utilities for Telite LMS.

This module provides secure password generation and management,
replacing hardcoded passwords with environment-based or generated passwords.
"""

from __future__ import annotations

import os
import secrets
import string


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Length of the password (minimum 12)
        
    Returns:
        Secure random password string
    """
    if length < 12:
        length = 12
    
    # Use a mix of uppercase, lowercase, digits, and special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    
    # Fill the rest randomly
    password.extend(secrets.choice(alphabet) for _ in range(length - 4))
    
    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def get_admin_password() -> str:
    """
    Get the global admin password from environment or generate one.
    
    In production, this MUST be set via TELITE_ADMIN_PASSWORD environment variable.
    In development, a secure password is generated and logged.
    
    Returns:
        Admin password string
        
    Raises:
        RuntimeError: If password not set in production environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    admin_password = os.getenv("TELITE_ADMIN_PASSWORD", "").strip()
    
    if admin_password:
        return admin_password
    
    # In production, password MUST be set
    if env in ("production", "prod", "staging"):
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: TELITE_ADMIN_PASSWORD must be set in production. "
            "Set this environment variable with a secure password."
        )
    
    # Development: Generate and log a secure password
    generated_password = generate_secure_password(16)
    print("\n" + "="*80)
    print("⚠️  WARNING: TELITE_ADMIN_PASSWORD not set!")
    print("="*80)
    print(f"Generated temporary admin password: {generated_password}")
    print("Username: globaladmin")
    print("Email: globaladmin@telite.io")
    print("\n⚠️  This password is for DEVELOPMENT ONLY!")
    print("⚠️  Set TELITE_ADMIN_PASSWORD environment variable for production!")
    print("="*80 + "\n")
    
    return generated_password


def get_default_learner_password() -> str:
    """
    Get the default learner password from environment or generate one.
    
    This is used for auto-approved signups and should be changed by users.
    
    Returns:
        Default learner password string
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    learner_password = os.getenv("TELITE_DEFAULT_LEARNER_PASSWORD", "").strip()
    
    if learner_password:
        return learner_password
    
    # In production, use a secure generated password
    if env in ("production", "prod", "staging"):
        return generate_secure_password(12)
    
    # Development: Use a simple but secure password
    return generate_secure_password(12)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, ""


def generate_reset_token() -> str:
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    import bcrypt
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(password: str, hashed_value: str) -> bool:
    if hashed_value.startswith(("$2a$", "$2b$", "$2y$")):
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_value.encode("utf-8"))
        except Exception:
            return False

    # Legacy PBKDF2 compatibility fallback
    import hashlib
    salt = os.getenv("TELITE_PASSWORD_SALT", "telite-dev-salt").encode("utf-8")
    candidate_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000).hex()
    if secrets.compare_digest(candidate_hash, hashed_value):
        return True

    legacy_salt = "telite-dev-salt"
    legacy_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        legacy_salt.encode("utf-8"),
        120_000,
    ).hex()
    return secrets.compare_digest(legacy_hash, hashed_value)
