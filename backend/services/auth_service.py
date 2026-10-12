"""Authentication service layer encapsulating business logic for user login and session status."""

from typing import Dict, Any, Optional

from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.exceptions import AuthenticationError
from backend.core.auth import create_access_token


class AuthService:
    """Service handling authentication credential verification and session status."""

    def __init__(self, config_handler: Optional[YAMLConfigHandler] = None) -> None:
        """Initializes auth service with configuration handler.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()

    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticates user credentials and generates JWT access token payload.

        Args:
            username (str): Target username string.
            password (str): Target password string.

        Returns:
            Dict[str, Any]: Access token dictionary payload.

        Raises:
            HTTPException: 401 Unauthorized if credentials do not match config.
        """
        config = self.config_handler.load_config()
        auth_cfg = config.auth

        if username != auth_cfg.username or password != auth_cfg.password:
            raise AuthenticationError("Invalid username or password.")

        access_token = create_access_token(
            data={"sub": auth_cfg.username},
            secret_key=auth_cfg.secret_key,
            algorithm=auth_cfg.algorithm,
            expires_delta_minutes=auth_cfg.token_expire_minutes,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_cfg.token_expire_minutes * 60,
        }

    def get_user_session_status(self, current_user: Optional[str]) -> Dict[str, Any]:
        """Retrieves session status information for current user.

        Args:
            current_user (Optional[str]): Username string if authenticated or None.

        Returns:
            Dict[str, Any]: User status payload.
        """
        try:
            config = self.config_handler.load_config()
            auth_enabled = config.auth.enabled
        except Exception:
            auth_enabled = False

        return {
            "username": current_user or "guest",
            "authenticated": bool(current_user) or not auth_enabled,
            "auth_enabled": auth_enabled,
        }
