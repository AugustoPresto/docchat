"""Shared request dependencies."""
import re

from fastapi import Header, HTTPException, status

from app.config import settings

LOCAL_OWNER = "local"
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def get_owner(x_client_id: str | None = Header(default=None)) -> str | None:
    """
    Anonymous, login-free ownership.

    The browser generates a random id and sends it as X-Client-Id. With
    ISOLATE_CLIENTS=true (public demo) every visitor only sees their own
    documents. Otherwise (local use) everything is shared and this returns
    None, meaning "no owner filter".
    """
    if not settings.isolate_clients:
        return None
    if not x_client_id or not _CLIENT_ID_RE.match(x_client_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or invalid X-Client-Id header.",
        )
    return x_client_id
