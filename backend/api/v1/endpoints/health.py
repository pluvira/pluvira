"""Health check API endpoint."""

from typing import Dict, Any
from fastapi import APIRouter, status

from backend.core.version import get_version_info

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
def check_health() -> Dict[str, Any]:
    """Checks operational status of the backend API daemon.

    Returns:
        Dict[str, Any]: Status payload with daemon state and version.
    """
    ver, git_hash = get_version_info()
    return {
        "status": "healthy",
        "service": "pluvira-backend",
        "version": ver,
        "git_hash": git_hash,
    }
