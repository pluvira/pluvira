"""Pluvira Cloud pairing and account management REST API endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, status, Depends

from backend.config.models import (
    CloudPairingStartResponse,
    CloudPairingStatusResponse,
    CloudAccountInfo,
    CloudBackupSnapshotItem,
    CloudBackupUploadPayload,
    CloudBackupUploadResponse,
    CloudBackupCreateUploadPayload,
    CloudBackupDecryptPayload,
    CloudBackupPinPayload,
    CloudBackupLatestDecryptPayload,
    LicenseActivationResponse,
)
from fastapi.responses import JSONResponse
from backend.services.cloud_pairing_service import CloudPairingService
from backend.services.system_service import SystemService

router = APIRouter()


def get_system_service() -> SystemService:
    """Dependency provider for SystemService instance."""
    return SystemService()


def get_cloud_pairing_service() -> CloudPairingService:
    """Dependency provider for CloudPairingService instance."""
    return CloudPairingService()


@router.post("/pairing/start", status_code=status.HTTP_200_OK, response_model=CloudPairingStartResponse)
async def start_cloud_pairing(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudPairingStartResponse:
    """Initiates RFC 8628 Device Authorization pairing with Pluvira Cloud.

    Returns:
        CloudPairingStartResponse: Device authorization codes and pairing verification URLs.
    """
    return await service.start_pairing()


@router.get("/pairing/status", status_code=status.HTTP_200_OK, response_model=CloudPairingStatusResponse)
def get_cloud_pairing_status(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudPairingStatusResponse:
    """Retrieves current state of device pairing session.

    Returns:
        CloudPairingStatusResponse: Active status, user code, and authorization outcome.
    """
    return service.get_pairing_status()


@router.post("/pairing/cancel", status_code=status.HTTP_200_OK)
def cancel_cloud_pairing(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, str]:
    """Cancels active device pairing session and halts background polling.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.cancel_pairing()
    return {"message": "Cloud pairing cancelled successfully."}


@router.get("/account", status_code=status.HTTP_200_OK, response_model=CloudAccountInfo)
def get_cloud_account(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudAccountInfo:
    """Retrieves linked Pluvira Cloud account identity information.

    Returns:
        CloudAccountInfo: Account UID, formatted Crockford ID, and link status.
    """
    return service.get_cloud_account_info()


@router.delete("/account", status_code=status.HTTP_200_OK)
def unlink_cloud_account(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, str]:
    """Unlinks Pluvira Cloud account and wipes local identity tokens.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.unlink_cloud_account()
    return {"message": "Cloud account unlinked successfully."}


@router.get("/backup/snapshots", status_code=status.HTTP_200_OK, response_model=list[CloudBackupSnapshotItem])
async def list_cloud_backup_snapshots(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> list[CloudBackupSnapshotItem]:
    """Retrieves list of stored E2EE backup snapshots from Pluvira Cloud vault.

    Returns:
        list[CloudBackupSnapshotItem]: List of backup snapshot records.
    """
    raw_list = await service.list_cloud_snapshots()
    return [CloudBackupSnapshotItem.model_validate(item) for item in raw_list]


@router.post("/backup/upload", status_code=status.HTTP_201_CREATED, response_model=CloudBackupUploadResponse)
async def upload_cloud_backup_snapshot(
    payload: CloudBackupUploadPayload,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudBackupUploadResponse:
    """Uploads a client-side encrypted backup blob to Pluvira Cloud E2EE vault.

    Args:
        payload (CloudBackupUploadPayload): Encrypted blob and checksum.

    Returns:
        CloudBackupUploadResponse: Confirmation and metadata.
    """
    res = await service.upload_cloud_snapshot(
        encrypted_blob=payload.encrypted_blob,
        sha256_checksum=payload.sha256_checksum,
        snapshot_label=payload.snapshot_label,
    )
    return CloudBackupUploadResponse.model_validate(res)


@router.get("/backup/download/latest", status_code=status.HTTP_200_OK)
async def download_latest_cloud_backup_snapshot(
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, Any]:
    """Downloads the latest encrypted backup blob from Pluvira Cloud vault.

    Returns:
        Dict[str, Any]: Snapshot blob payload for the latest snapshot.
    """
    return await service.download_latest_cloud_snapshot()


@router.get("/backup/download/{backup_id}", status_code=status.HTTP_200_OK)
async def download_cloud_backup_snapshot(
    backup_id: str,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, Any]:
    """Downloads an encrypted backup blob from Pluvira Cloud vault.

    Args:
        backup_id (str): Target snapshot identifier.

    Returns:
        Dict[str, Any]: Snapshot blob payload.
    """
    return await service.download_cloud_snapshot(backup_id)


@router.delete("/backup/{backup_id}", status_code=status.HTTP_200_OK)
async def delete_cloud_backup_snapshot(
    backup_id: str,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, str]:
    """Deletes an E2EE backup snapshot from Pluvira Cloud vault.

    Args:
        backup_id (str): Target snapshot identifier.

    Returns:
        Dict[str, str]: Operation status message.
    """
    await service.delete_cloud_snapshot(backup_id)
    return {"message": f"Cloud backup snapshot '{backup_id}' deleted successfully."}


@router.patch("/backup/{backup_id}/pin", status_code=status.HTTP_200_OK, response_model=CloudBackupSnapshotItem)
async def pin_cloud_backup_snapshot(
    backup_id: str,
    payload: CloudBackupPinPayload,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudBackupSnapshotItem:
    """Updates the pinning lock status of a cloud backup snapshot against FIFO auto-purge.

    Args:
        backup_id (str): Target snapshot identifier.
        payload (CloudBackupPinPayload): Pin status payload.

    Returns:
        CloudBackupSnapshotItem: Updated snapshot item record.
    """
    res = await service.pin_cloud_snapshot(backup_id, payload.is_pinned)
    return CloudBackupSnapshotItem.model_validate(res)


@router.post("/backup/create-and-upload", status_code=status.HTTP_201_CREATED, response_model=CloudBackupUploadResponse)
async def create_and_upload_cloud_backup(
    payload: CloudBackupCreateUploadPayload,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> CloudBackupUploadResponse:
    """Exports local SQLite configuration, encrypts via AES-256-GCM, and uploads to cloud vault."""
    res = await service.create_and_upload_cloud_snapshot(
        passphrase=payload.passphrase,
        snapshot_label=payload.snapshot_label,
        pin_snapshot=payload.pin_snapshot,
    )
    return CloudBackupUploadResponse.model_validate(res)


@router.post("/backup/download-and-decrypt", status_code=status.HTTP_200_OK)
async def download_and_decrypt_cloud_backup(
    payload: CloudBackupDecryptPayload,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, Any]:
    """Downloads encrypted snapshot from cloud vault and decrypts on local backend."""
    return await service.download_and_decrypt_cloud_snapshot(
        backup_id=payload.backup_id,
        passphrase=payload.passphrase,
    )


@router.post("/backup/download-latest-and-decrypt", status_code=status.HTTP_200_OK)
async def download_latest_and_decrypt_cloud_backup(
    payload: CloudBackupLatestDecryptPayload,
    service: CloudPairingService = Depends(get_cloud_pairing_service),
) -> Dict[str, Any]:
    """Downloads the latest encrypted snapshot from cloud vault and decrypts on local backend."""
    return await service.download_latest_and_decrypt_cloud_snapshot(
        passphrase=payload.passphrase,
    )


@router.post(
    "/sync-license",
    status_code=status.HTTP_200_OK,
    response_model=LicenseActivationResponse,
    responses={
        400: {"model": LicenseActivationResponse, "description": "Validation error or account not linked"},
        403: {"model": LicenseActivationResponse, "description": "Invalid, expired, or revoked license"},
    },
)
def sync_license_m2m(
    service: SystemService = Depends(get_system_service),
) -> Any:
    """Synchronizes active Pro license via M2M Device-Bound authorization with Pluvira Cloud."""
    result = service.sync_cloud_license()
    if not result.get("success"):
        err_code = result.get("error_code") or result.get("code") or "SYNC_FAILED"
        status_code = (
            status.HTTP_403_FORBIDDEN
            if err_code in ("LICENSE_EXPIRED", "LICENSE_INVALID_SIGNATURE", "DEVICE_REVOKED", "NO_ACTIVE_LICENSE_FOUND")
            else status.HTTP_400_BAD_REQUEST
        )
        result["detail"] = result.get("message")
        result["code"] = err_code
        return JSONResponse(status_code=status_code, content=result)
    return result
