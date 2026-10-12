"""System status and update execution REST endpoints."""

from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, status, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse

from backend.services.system_service import SystemService
from backend.core.utils import ParamUtils
from backend.config.models import (
    UpdateProgressDTO,
    SystemUpdatePayload,
    TrialClaimPayload,
    ActivateLicensePayload,
    LicenseActivationResponse,
    BulletinListResponse,
    BulletinDismissResponse,
    BulletinReadResponse,
)
from backend.core.exceptions import EntityNotFoundError

router = APIRouter()


def get_system_service() -> SystemService:
    """Dependency provider for SystemService instance."""
    return SystemService()


@router.get("/status", status_code=status.HTTP_200_OK)
def get_system_status(
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Retrieves current execution status of the system.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: Dictionary with execution state and status string.
    """
    return service.get_status()


@router.get("/license", status_code=status.HTTP_200_OK)
def get_system_license(
    force_online: bool = Query(True, description="Execute online heartbeat check against Pluvira Cloud"),
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Retrieves detailed Pro license lifecycle, error codes, and entitlement metadata.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: License metadata payload.
    """
    return service.get_license_info(force_online=force_online)


@router.post("/license/trial", status_code=status.HTTP_200_OK)
def claim_pro_trial(
    payload: Optional[TrialClaimPayload] = None,
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Claims and activates 14-day on-demand Pro trial license.

    Args:
        payload (Optional[TrialClaimPayload]): Optional token and cloud URL parameters.
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: Updated license details dictionary.
    """
    token = payload.token if payload else None
    cloud_url = payload.cloud_url if payload else None
    return service.claim_trial_license(token=token, cloud_url=cloud_url)


@router.post(
    "/license/activate",
    status_code=status.HTTP_200_OK,
    response_model=LicenseActivationResponse,
    responses={
        400: {"model": LicenseActivationResponse, "description": "Validation error"},
        403: {"model": LicenseActivationResponse, "description": "Invalid or expired token"},
    },
)
def activate_pro_license(
    payload: ActivateLicensePayload,
    service: SystemService = Depends(get_system_service),
) -> Union[LicenseActivationResponse, JSONResponse]:
    """Activates and verifies a commercial Pro license token.

    Args:
        payload (ActivateLicensePayload): License token payload.
        service (SystemService): SystemService dependency instance.

    Returns:
        LicenseActivationResponse: Activation status and license metadata.
    """
    result = service.activate_license(payload.token)
    if not result.get("success"):
        err_code = result.get("error_code")
        status_code = (
            status.HTTP_403_FORBIDDEN
            if err_code in ("LICENSE_EXPIRED", "LICENSE_INVALID_SIGNATURE", "LICENSE_HANDSHAKE_FAILED")
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(status_code=status_code, content=result)
    return result


@router.post(
    "/license/sync-cloud",
    status_code=status.HTTP_200_OK,
    response_model=LicenseActivationResponse,
    responses={
        400: {"model": LicenseActivationResponse, "description": "Validation error or account not linked"},
        403: {"model": LicenseActivationResponse, "description": "Invalid or expired token"},
    },
)
def sync_pro_license_from_cloud(
    service: SystemService = Depends(get_system_service),
) -> Any:
    """Fetches and activates the latest active license token from Pluvira Cloud portal.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        LicenseActivationResponse: Activation status and license metadata.
    """
    result = service.sync_cloud_license()
    if not result.get("success"):
        err_code = result.get("error_code") or "CLOUD_SYNC_FAILED"
        status_code = (
            status.HTTP_403_FORBIDDEN
            if err_code in ("LICENSE_EXPIRED", "LICENSE_INVALID_SIGNATURE", "LICENSE_HANDSHAKE_FAILED")
            else status.HTTP_400_BAD_REQUEST
        )
        result["detail"] = result.get("message")
        result["code"] = err_code
        return JSONResponse(status_code=status_code, content=result)
    return result


@router.post("/update", status_code=status.HTTP_202_ACCEPTED)
def trigger_system_update(
    payload: Optional[SystemUpdatePayload] = None,
    mode: Optional[str] = Query(None, description="Legacy execution mode query parameter"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: SystemService = Depends(get_system_service),
) -> Dict[str, str]:
    """Triggers background acquisition and update process.

    Args:
        payload (Optional[SystemUpdatePayload]): System update request payload.
        mode (Optional[str]): Legacy mode query parameter.
        background_tasks (BackgroundTasks): FastAPI background tasks dependency.
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, str]: Status message.
    """
    exec_mode = ParamUtils.resolve_param(
        payload.mode if payload else None, mode, "full"
    )
    return service.trigger_update(exec_mode, background_tasks, trigger="manual")


@router.get("/update/progress", status_code=status.HTTP_200_OK, response_model=UpdateProgressDTO)
def get_update_progress(
    service: SystemService = Depends(get_system_service),
) -> UpdateProgressDTO:
    """Retrieves real-time structured progress DTO for background update task.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        UpdateProgressDTO: Structured update progress snapshot.
    """
    return UpdateProgressDTO(**service.get_update_progress())


@router.get("/logs", status_code=status.HTTP_200_OK)
def get_system_logs(
    max_items: int = Query(100, ge=1, le=1000),
    service: SystemService = Depends(get_system_service),
) -> List[str]:
    """Retrieves recent execution runtime logs from real-time queue.

    Args:
        max_items (int): Max log lines to consume.
        service (SystemService): SystemService dependency instance.

    Returns:
        List[str]: List of log message strings.
    """
    return service.get_logs(max_items=max_items)


@router.post("/cache/clear", status_code=status.HTTP_200_OK)
def clear_system_cache(
    service: SystemService = Depends(get_system_service),
) -> Dict[str, str]:
    """Explicitly clears temporary RAM storage and volatile caches.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    return service.clear_cache()


@router.post("/factory-reset", status_code=status.HTTP_200_OK)
def factory_reset(
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Performs full system factory reset restoring configs and databases to initial state.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: Operation success status and message.
    """
    return service.factory_reset()


@router.get("/bulletins", status_code=status.HTTP_200_OK, response_model=BulletinListResponse)
def get_system_bulletins(
    include_dismissed: bool = Query(False, description="Whether to include dismissed bulletins"),
    service: SystemService = Depends(get_system_service),
) -> BulletinListResponse:
    """Retrieves active system broadcast bulletins.

    Args:
        include_dismissed (bool): Include dismissed bulletins in list.
        service (SystemService): SystemService dependency instance.

    Returns:
        BulletinListResponse: List of active bulletins and counts.
    """
    bulletins = service.get_active_bulletins(include_dismissed=include_dismissed)
    unread = [b for b in bulletins if not b.is_dismissed]
    return BulletinListResponse(
        bulletins=bulletins,
        total=len(bulletins),
        unread_count=len(unread),
    )


@router.post("/bulletins/{bulletin_id}/dismiss", status_code=status.HTTP_200_OK, response_model=BulletinDismissResponse)
def dismiss_system_bulletin(
    bulletin_id: str,
    service: SystemService = Depends(get_system_service),
) -> BulletinDismissResponse:
    """Marks a system bulletin as dismissed instance-wide.

    Args:
        bulletin_id (str): Target bulletin identifier.
        service (SystemService): SystemService dependency instance.

    Returns:
        BulletinDismissResponse: Dismissal confirmation report.
    """
    success = service.dismiss_bulletin(bulletin_id)
    if not success:
        raise EntityNotFoundError(f"Bulletin with ID '{bulletin_id}' not found.")
    return BulletinDismissResponse(id=bulletin_id, is_dismissed=True)


@router.post("/bulletins/{bulletin_id}/read", status_code=status.HTTP_200_OK, response_model=BulletinReadResponse)
def mark_system_bulletin_read(
    bulletin_id: str,
    service: SystemService = Depends(get_system_service),
) -> BulletinReadResponse:
    """Marks a system bulletin as read/viewed in viewport instance-wide.

    Args:
        bulletin_id (str): Target bulletin identifier.
        service (SystemService): SystemService dependency instance.

    Returns:
        BulletinReadResponse: Read confirmation report.
    """
    success = service.mark_bulletin_read(bulletin_id)
    if not success:
        raise EntityNotFoundError(f"Bulletin with ID '{bulletin_id}' not found.")
    return BulletinReadResponse(id=bulletin_id, is_read=True)


@router.delete("/bulletins", status_code=status.HTTP_200_OK)
def clear_archived_bulletins(
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Clears all archived (dismissed) system bulletins.

    Args:
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: Clear confirmation report with count.
    """
    count = service.clear_archived_bulletins()
    return {
        "success": True,
        "deleted_count": count,
        "message": f"Successfully deleted {count} archived bulletin(s).",
    }


@router.delete("/bulletins/{bulletin_id}", status_code=status.HTTP_200_OK)
def delete_system_bulletin(
    bulletin_id: str,
    service: SystemService = Depends(get_system_service),
) -> Dict[str, Any]:
    """Deletes a single system bulletin by ID.

    Args:
        bulletin_id (str): Target bulletin identifier.
        service (SystemService): SystemService dependency instance.

    Returns:
        Dict[str, Any]: Deletion confirmation report.
    """
    success = service.delete_bulletin(bulletin_id)
    if not success:
        raise EntityNotFoundError(f"Bulletin with ID '{bulletin_id}' not found.")
    return {
        "id": bulletin_id,
        "deleted": True,
        "message": "Bulletin deleted successfully",
    }
