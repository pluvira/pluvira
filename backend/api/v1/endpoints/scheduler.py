"""Scheduler configuration management REST API endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, status, Depends, Query
from pydantic import BaseModel, Field

from backend.config.models import SchedulePayload
from backend.services.scheduler_service import SchedulerService

router = APIRouter()


class RestoreDefaultsPayload(BaseModel):
    """Payload for restoring default scheduler jobs."""

    mode: str = Field(default="missing_only", description="Restoration mode ('missing_only' or 'full_reset')")


def get_scheduler_service() -> SchedulerService:
    """Dependency provider for SchedulerService instance."""
    return SchedulerService()


@router.get("", status_code=status.HTTP_200_OK)
def get_schedule_configuration(service: SchedulerService = Depends(get_scheduler_service)) -> Dict[str, Any]:
    """Retrieves background schedule configuration from schedule.yaml.

    Returns:
        Dict[str, Any]: Schedule configuration dictionary.
    """
    return service.get_schedule_config()


@router.put("", status_code=status.HTTP_200_OK)
def update_schedule_configuration(
    payload: SchedulePayload, service: SchedulerService = Depends(get_scheduler_service)
) -> Dict[str, Any]:
    """Updates schedule configuration in schedule.yaml and synchronizes jobs.

    Args:
        payload (SchedulePayload): Schedule configuration payload.

    Returns:
        Dict[str, Any]: Updated schedule configuration.
    """
    return service.update_schedule_config(payload.model_dump())


@router.post("/restore-defaults", status_code=status.HTTP_200_OK)
def restore_default_scheduler_jobs(
    payload: Optional[RestoreDefaultsPayload] = None,
    mode: Optional[str] = Query(None, description="Restoration mode ('missing_only' or 'full_reset')"),
    service: SchedulerService = Depends(get_scheduler_service),
) -> Dict[str, Any]:
    """Restores default system and recommended background scheduled tasks.

    Args:
        payload (Optional[RestoreDefaultsPayload]): Request payload.
        mode (Optional[str]): Convenience query parameter.
        service (SchedulerService): SchedulerService dependency.

    Returns:
        Dict[str, Any]: Updated schedule configuration.
    """
    selected_mode = (payload.mode if payload and payload.mode else None) or mode or "missing_only"
    return service.restore_default_jobs(mode=selected_mode)
