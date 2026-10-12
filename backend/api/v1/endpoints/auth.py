"""Authentication REST API v1 endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, status, Depends

from backend.config.models import LoginPayload
from backend.api.deps import get_current_user, get_optional_current_user
from backend.services.auth_service import AuthService

router = APIRouter()


def get_auth_service() -> AuthService:
    """Dependency provider for AuthService instance."""
    return AuthService()



@router.post("/login", status_code=status.HTTP_200_OK)
def login_for_access_token(
    payload: LoginPayload, service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Authenticates admin credentials and returns a JWT access token.

    Args:
        payload (LoginPayload): User login credentials.

    Returns:
        Dict[str, Any]: Bearer JWT access token response.
    """
    return service.authenticate_user(payload.username, payload.password)


@router.get("/me", status_code=status.HTTP_200_OK)
def get_authenticated_user_status(
    current_user: Optional[str] = Depends(get_optional_current_user),
    service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Retrieves current authenticated user session status.

    Args:
        current_user (Optional[str]): Username returned by get_current_user dependency.

    Returns:
        Dict[str, Any]: User status payload.
    """
    return service.get_user_session_status(current_user)
