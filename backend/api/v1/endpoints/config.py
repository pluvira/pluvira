"""Configuration management REST endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, status, Query, Depends
from backend.core.exceptions import ValidationDomainError
from backend.config.models import (
    GlobalConfig,
    NotificationPresetPayload,
    TestNotificationPayload,
)
from backend.services.config_service import ConfigService
from backend.services.notification_service import NotificationService
from backend.core.utils import ParamUtils

router = APIRouter()


def get_config_service() -> ConfigService:
    """Dependency provider for ConfigService instance."""
    return ConfigService()


def get_notification_service() -> NotificationService:
    """Dependency provider for NotificationService instance."""
    return NotificationService()


@router.get("", status_code=status.HTTP_200_OK)
def get_configuration(service: ConfigService = Depends(get_config_service)) -> Dict[str, Any]:
    """Retrieves current static GlobalConfig object from YAML with relational metadata rewrites.

    Returns:
        Dict[str, Any]: Pydantic configuration model dictionary with populated global rewrites.
    """
    cfg = service.get_config()
    data = cfg.model_dump()
    data["settings"]["rewrites"] = [r.model_dump() for r in (cfg.settings.rewrites or [])]
    if cfg.settings.notifications is not None:
        data["settings"]["notifications"] = cfg.settings.notifications.model_dump()
        data["settings"]["notification_urls"] = list(cfg.settings.notifications.urls)
    return data


@router.put("", status_code=status.HTTP_200_OK)
def update_configuration(
    config_payload: GlobalConfig, service: ConfigService = Depends(get_config_service)
) -> Dict[str, Any]:
    """Validates and persists updated GlobalConfig object back to YAML file and SQLite metadata rules.

    Args:
        config_payload (GlobalConfig): Validated configuration payload.

    Returns:
        Dict[str, Any]: Saved configuration model dictionary with populated global rewrites.
    """
    updated = service.update_config(config_payload)
    data = updated.model_dump()
    data["settings"]["rewrites"] = [r.model_dump() for r in (updated.settings.rewrites or [])]
    if updated.settings.notifications is not None:
        data["settings"]["notifications"] = updated.settings.notifications.model_dump()
        data["settings"]["notification_urls"] = list(updated.settings.notifications.urls)
    return data


@router.post("/notifications/preset", status_code=status.HTTP_200_OK)
def apply_notification_preset_profile(
    payload: Optional[NotificationPresetPayload] = None,
    name: Optional[str] = Query(None, description="Preset profile name (legacy query parameter)"),
    service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:
    """Applies a preset notification event profile to configuration.

    Args:
        payload (Optional[NotificationPresetPayload]): Preset profile request payload.
        name (Optional[str]): Legacy query parameter.

    Returns:
        Dict[str, Any]: Updated notification settings object.
    """
    preset_name = ParamUtils.resolve_param(
        payload.name if payload else None, name, ""
    )
    if not preset_name:
        raise ValidationDomainError("Notification preset profile name is required.")
    return service.apply_preset(preset_name)


@router.post("/notifications/test", status_code=status.HTTP_200_OK)
def send_test_notification(
    payload: Optional[TestNotificationPayload] = None,
    service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:
    """Dispatches a test notification message to all configured notification targets.

    Args:
        payload (Optional[TestNotificationPayload]): Test notification title and body.

    Returns:
        Dict[str, Any]: Operation status message and target counts.
    """
    title = payload.title if payload else None
    body = payload.body if payload else None
    return service.send_test_notification(title=title, body=body)
