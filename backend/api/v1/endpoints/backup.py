"""Configuration backup and restore REST API endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, status, Query, Response, Depends, BackgroundTasks

from backend.services.backup_service import BackupService
from backend.core.backup.bundle import (
    BackupValidationResult,
    BackupImportPayload,
    BackupImportResult,
)

router = APIRouter()


def get_backup_service() -> BackupService:
    """Dependency provider for BackupService instance."""
    return BackupService()


@router.get("/export", status_code=status.HTTP_200_OK)
def export_backup(
    sanitized: bool = Query(False, description="Mask sensitive credentials and webhook tokens"),
    service: BackupService = Depends(get_backup_service),
) -> Response:
    """Generates and downloads a unified JSON backup bundle.

    Args:
        sanitized (bool): Whether to sanitize sensitive data.

    Returns:
        Response: JSON file attachment response.
    """
    bundle = service.export_backup(sanitized=sanitized)
    
    content = bundle.model_dump_json(by_alias=True, exclude_none=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"pluvira_backup_{timestamp}.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/validate", status_code=status.HTTP_200_OK, response_model=BackupValidationResult)
def validate_backup(
    payload: BackupImportPayload, service: BackupService = Depends(get_backup_service)
) -> BackupValidationResult:
    """Performs pre-flight validation and diff calculation for an incoming backup bundle.

    Args:
        payload (BackupImportPayload): Backup bundle and import mode.

    Returns:
        BackupValidationResult: Validation report and diff summary.
    """
    return service.validate_backup(bundle_input=payload.bundle, mode=payload.mode)


@router.post("/import", status_code=status.HTTP_200_OK, response_model=BackupImportResult)
def import_backup(
    payload: BackupImportPayload,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: BackupService = Depends(get_backup_service),
) -> BackupImportResult:
    """Imports a backup bundle with transactional safety snapshots and auto-rollback.

    Args:
        payload (BackupImportPayload): Backup bundle and import mode.

    Returns:
        BackupImportResult: Import execution report.
    """
    return service.import_backup(
        bundle_input=payload.bundle,
        mode=payload.mode,
        trigger_sync=payload.trigger_sync,
        background_tasks=background_tasks,
    )
