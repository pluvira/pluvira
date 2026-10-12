"""IPTV M3U sources resource management REST API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, status, BackgroundTasks, Depends

from backend.services.source_service import SourceService
from backend.config.models import (
    Source,
    BulkSourceStatusPayload,
    BulkSourceDeletePayload,
    BulkSourceUserAgentPayload,
    BulkSourceReorderPayload,
    BulkSourceRefreshPayload,
)

router = APIRouter()


def get_source_service() -> SourceService:
    """Dependency provider for SourceService instance."""
    return SourceService()


@router.get("", status_code=status.HTTP_200_OK)
def get_sources(service: SourceService = Depends(get_source_service)) -> List[Dict[str, Any]]:
    """Retrieves list of configured IPTV M3U sources.

    Returns:
        List[Dict[str, Any]]: List of source model dictionaries.
    """
    return service.get_sources()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source(
    source_payload: Source, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Adds a new IPTV M3U source to configuration.

    Args:
        source_payload (Source): Source model payload.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Created source dictionary.
    """
    return service.create_source(source_payload)


@router.patch("/{source_name}/toggle", status_code=status.HTTP_200_OK)
def toggle_source_status(
    source_name: str, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Toggles enabled status for a specific IPTV M3U source.

    Args:
        source_name (str): IPTV source provider name.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Updated source status dictionary.
    """
    return service.toggle_source_status(source_name)


@router.delete("/{source_name}", status_code=status.HTTP_200_OK)
def delete_source(
    source_name: str, service: SourceService = Depends(get_source_service)
) -> Dict[str, str]:
    """Removes an IPTV M3U source from configuration.

    Args:
        source_name (str): IPTV source provider name to remove.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_source(source_name)
    return {"message": f"Source '{source_name}' deleted successfully."}


@router.post("/bulk/status", status_code=status.HTTP_200_OK)
def bulk_update_source_status(
    payload: BulkSourceStatusPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Bulk enables, disables, or toggles status for multiple IPTV M3U sources.

    Args:
        payload (BulkSourceStatusPayload): Target names and action.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_update_source_status(payload.names, payload.action)


@router.post("/bulk/delete", status_code=status.HTTP_200_OK)
def bulk_delete_sources(
    payload: BulkSourceDeletePayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Deletes multiple IPTV M3U sources in bulk.

    Args:
        payload (BulkSourceDeletePayload): Target names to delete.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_delete_sources(payload.names)


@router.post("/bulk/user-agent", status_code=status.HTTP_200_OK)
def bulk_update_source_user_agent(
    payload: BulkSourceUserAgentPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Updates or resets User-Agent header in bulk for multiple IPTV M3U sources.

    Args:
        payload (BulkSourceUserAgentPayload): Target names and User-Agent.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_update_source_user_agent(payload.names, payload.user_agent)


@router.post("/bulk/reorder", status_code=status.HTTP_200_OK)
def bulk_reorder_sources(
    payload: BulkSourceReorderPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Reorders IPTV M3U sources sequentially based on the provided names list.

    Args:
        payload (BulkSourceReorderPayload): Ordered source names list.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_reorder_sources(payload.names)


@router.post("/bulk/refresh", status_code=status.HTTP_202_ACCEPTED)
def bulk_refresh_sources(
    payload: BulkSourceRefreshPayload,
    background_tasks: BackgroundTasks,
    service: SourceService = Depends(get_source_service),
) -> Dict[str, str]:
    """Triggers background acquisition refresh for specific M3U sources.

    Args:
        payload (BulkSourceRefreshPayload): Target source names.
        background_tasks (BackgroundTasks): FastAPI background tasks dependency.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    return service.bulk_refresh_sources(payload.names, background_tasks)
