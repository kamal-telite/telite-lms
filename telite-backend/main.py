"""Compatibility entrypoint for local tools and `uvicorn main:app`."""

import os as _os
import pathlib as _pathlib

# Auto-load .env from the backend directory so `uvicorn main:app` always
# picks up the correct secrets — no --env-file flag required.
_env_file = _pathlib.Path(__file__).parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv as _load_dotenv
        _load_dotenv(dotenv_path=_env_file, override=False)
    except ImportError:
        # python-dotenv not installed — fall back to manual parsing
        with open(_env_file) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _, _v = _line.partition("=")
                    _os.environ.setdefault(_k.strip(), _v.strip())

from app.main import app, create_app  # noqa: E402

__all__ = ["app", "create_app"]
