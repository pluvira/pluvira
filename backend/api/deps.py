"""FastAPI security and common route dependencies."""

from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from threading import Lock
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.auth import decode_access_token

security_scheme = HTTPBearer(auto_error=False)

_cached_config = None
_cached_config_mtime = 0.0
_cached_config_path = None
_config_cache_lock = Lock()


def _get_cached_config():
    """Returns mtime-cached GlobalConfig instance to eliminate disk I/O on every request."""
    global _cached_config, _cached_config_mtime, _cached_config_path
    handler = YAMLConfigHandler()
    file_path = getattr(handler, "file_path", None)
    mtime = 0.0
    if file_path:
        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            mtime = 0.0

    with _config_cache_lock:
        if (
            _cached_config is not None
            and _cached_config_path == file_path
            and mtime == _cached_config_mtime
        ):
            return _cached_config

        try:
            loaded = handler.load_config()
            _cached_config = loaded
            _cached_config_mtime = mtime
            _cached_config_path = file_path
            return loaded
        except Exception:
            return _cached_config


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[str]:
    """FastAPI dependency verifying Bearer JWT token if auth is enabled.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Bearer credentials.

    Returns:
        Optional[str]: Username string if authenticated or None if auth is disabled.

    Raises:
        HTTPException: 401 Unauthorized if auth is enabled and token is missing or invalid.
    """
    config = _get_cached_config()
    if not config:
        return None

    auth_cfg = getattr(config, "auth", None)
    if not auth_cfg or not auth_cfg.enabled:
        return None

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(
        credentials.credentials,
        secret_key=auth_cfg.secret_key,
        algorithm=auth_cfg.algorithm,
    )
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload["sub"]


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[str]:
    """FastAPI dependency extracting username if valid Bearer token provided, returning None otherwise.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Bearer credentials.

    Returns:
        Optional[str]: Username string if authenticated, None otherwise.
    """
    if not credentials or not credentials.credentials:
        return None

    config = _get_cached_config()
    if not config:
        return None

    auth_cfg = getattr(config, "auth", None)
    if not auth_cfg or not auth_cfg.enabled:
        return None

    payload = decode_access_token(
        credentials.credentials,
        secret_key=auth_cfg.secret_key,
        algorithm=auth_cfg.algorithm,
    )
    if not payload or not payload.get("sub"):
        return None

    return payload["sub"]
