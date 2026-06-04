from __future__ import annotations

from contextvars import ContextVar, Token


_request_id: ContextVar[str | None] = ContextVar("telite_request_id", default=None)


def set_request_id(value: str) -> Token:
    return _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)
