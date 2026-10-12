"""EPG guide sources and programmes REST endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Query, BackgroundTasks, Depends

from backend.services.source_service import SourceService
from backend.services.epg_service import EpgService
from backend.config.models import (
    EPGSource,
    BulkSourceStatusPayload as BulkEPGSourceStatusPayload,
    BulkSourceDeletePayload as BulkEPGSourceDeletePayload,
    BulkSourceUserAgentPayload as BulkEPGSourceUserAgentPayload,
    BulkSourceReorderPayload as BulkEPGSourceReorderPayload,
    BulkSourceRefreshPayload as BulkEPGSourceRefreshPayload,
    EpgProgrammesSearchPayload,
)
router = APIRouter()


def get_source_service() -> SourceService:
    """Dependency provider for SourceService instance."""
    return SourceService()


def get_epg_service() -> EpgService:
    """Dependency provider for EpgService instance."""
    return EpgService()


@router.get("/sources", status_code=status.HTTP_200_OK)
def get_epg_sources(service: SourceService = Depends(get_source_service)) -> List[Dict[str, Any]]:
    """Retrieves list of configured global EPG sources.

    Returns:
        List[Dict[str, Any]]: List of EPG source objects.
    """
    return service.get_epg_sources()


@router.get("/channels", status_code=status.HTTP_200_OK)
def get_epg_channels(
    source: Optional[str] = Query(None, description="Filter by EPG source name"),
    search: Optional[str] = Query(None, description="Filter by channel display name or raw EPG ID"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    service: EpgService = Depends(get_epg_service),
) -> List[Dict[str, Any]]:
    """Retrieves indexed EPG channels with optional source filtering and search query.

    Args:
        source (Optional[str]): Optional EPG guide source name filter.
        search (Optional[str]): Optional partial search query matching name or raw ID.
        limit (int): Maximum items to return (default 100, max 500).
        service (EpgService): EpgService dependency instance.

    Returns:
        List[Dict[str, Any]]: List of channel items with id, raw_id, name, source.
    """
    return service.get_epg_channels(source=source, search=search, limit=limit)


@router.post("/sources", status_code=status.HTTP_201_CREATED)
def create_epg_source(
    epg_source_payload: EPGSource, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Adds a new global EPG source to configuration.

    Args:
        epg_source_payload (EPGSource): EPG source model payload.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Created EPG source dictionary.
    """
    return service.create_epg_source(epg_source_payload)


@router.patch("/sources/{source_name}/toggle", status_code=status.HTTP_200_OK)
def toggle_epg_source_status(
    source_name: str, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Toggles enabled status for a specific global EPG source.

    Args:
        source_name (str): EPG guide source name.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Updated EPG source status dictionary.
    """
    return service.toggle_epg_source_status(source_name)


@router.delete("/sources/{source_name}", status_code=status.HTTP_200_OK)
def delete_epg_source(
    source_name: str, service: SourceService = Depends(get_source_service)
) -> Dict[str, str]:
    """Removes a global EPG source from configuration.

    Args:
        source_name (str): EPG guide source name to remove.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_epg_source(source_name)
    return {"message": f"EPG source '{source_name}' deleted successfully."}


@router.post("/sources/bulk/status", status_code=status.HTTP_200_OK)
def bulk_update_epg_source_status(
    payload: BulkEPGSourceStatusPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Bulk enables, disables, or toggles status for multiple global EPG sources.

    Args:
        payload (BulkEPGSourceStatusPayload): Target names and action.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_update_epg_source_status(payload.names, payload.action)


@router.post("/sources/bulk/delete", status_code=status.HTTP_200_OK)
def bulk_delete_epg_sources(
    payload: BulkEPGSourceDeletePayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Deletes multiple global EPG sources in bulk.

    Args:
        payload (BulkEPGSourceDeletePayload): Target names to delete.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_delete_epg_sources(payload.names)


@router.post("/sources/bulk/user-agent", status_code=status.HTTP_200_OK)
def bulk_update_epg_source_user_agent(
    payload: BulkEPGSourceUserAgentPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Updates or resets User-Agent header in bulk for multiple global EPG sources.

    Args:
        payload (BulkEPGSourceUserAgentPayload): Target names and User-Agent.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_update_epg_source_user_agent(payload.names, payload.user_agent)


@router.post("/sources/bulk/reorder", status_code=status.HTTP_200_OK)
def bulk_reorder_epg_sources(
    payload: BulkEPGSourceReorderPayload, service: SourceService = Depends(get_source_service)
) -> Dict[str, Any]:
    """Reorders global EPG sources sequentially based on the provided names list.

    Args:
        payload (BulkEPGSourceReorderPayload): Ordered EPG source names list.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, Any]: Operation status dictionary.
    """
    return service.bulk_reorder_epg_sources(payload.names)


@router.post("/sources/bulk/refresh", status_code=status.HTTP_202_ACCEPTED)
def bulk_refresh_epg_sources(
    payload: BulkEPGSourceRefreshPayload,
    background_tasks: BackgroundTasks,
    service: SourceService = Depends(get_source_service),
) -> Dict[str, str]:
    """Triggers background acquisition refresh for specific EPG sources.

    Args:
        payload (BulkEPGSourceRefreshPayload): Target EPG source names.
        background_tasks (BackgroundTasks): FastAPI background tasks dependency.
        service (SourceService): SourceService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    return service.bulk_refresh_epg_sources(payload.names, background_tasks)


@router.post("/programmes/search", status_code=status.HTTP_200_OK)
def search_epg_programmes(
    payload: EpgProgrammesSearchPayload, service: EpgService = Depends(get_epg_service)
) -> Dict[str, Any]:
    """Retrieves EPG programme schedules using JSON body filter criteria.

    Args:
        payload (EpgProgrammesSearchPayload): EPG search criteria payload.
        service (EpgService): EpgService dependency instance.

    Returns:
        Dict[str, Any]: Map of EPG IDs to list of programme dicts.
    """
    return service.get_programmes(
        ids=payload.ids,
        date=payload.date,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )


@router.get("/programmes", status_code=status.HTTP_200_OK)
def get_epg_programmes(
    ids: str = Query(..., description="Comma-separated namespaced EPG channel IDs"),
    date: str = Query(None, description="Filter programmes by specific date (YYYY-MM-DD)"),
    date_from: str = Query(None, description="Filter programmes starting from date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="Filter programmes ending before date (YYYY-MM-DD)"),
    service: EpgService = Depends(get_epg_service),
) -> Dict[str, Any]:
    """Retrieves EPG programme schedules for target channel IDs using DataProcessor cache.

    Args:
        ids (str): Comma-separated list of namespaced EPG IDs.
        date (str, optional): Specific date filter.
        date_from (str, optional): Start date filter.
        date_to (str, optional): End date filter.
        service (EpgService): EpgService dependency instance.

    Returns:
        Dict[str, Any]: Map of EPG IDs to list of programme dicts.
    """
    return service.get_programmes(ids, date, date_from, date_to)
