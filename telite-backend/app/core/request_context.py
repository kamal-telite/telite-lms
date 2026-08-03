from __future__ import annotations

from contextvars import ContextVar, Token


_request_id: ContextVar[str | None] = ContextVar("telite_request_id", default=None)
_org_id: ContextVar[int | None] = ContextVar("telite_org_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("telite_user_id", default=None)
_endpoint: ContextVar[str | None] = ContextVar("telite_endpoint", default=None)
_http_method: ContextVar[str | None] = ContextVar("telite_http_method", default=None)


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_org_id(value: int | None) -> Token:
    return _org_id.set(value)


def get_org_id() -> int | None:
    return _org_id.get()


def set_user_id(value: str | None) -> Token:
    return _user_id.set(value)


def get_user_id() -> str | None:
    return _user_id.get()


def set_endpoint(value: str | None) -> Token:
    return _endpoint.set(value)


def get_endpoint() -> str | None:
    return _endpoint.get()


def set_http_method(value: str | None) -> Token:
    return _http_method.set(value)


def get_http_method() -> str | None:
    return _http_method.get()


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def reset_all_context() -> None:
    """Reset all context variables (useful for testing or cleanup)."""
    _request_id.set(None)
    _org_id.set(None)
    _user_id.set(None)
    _endpoint.set(None)
    _http_method.set(None)
