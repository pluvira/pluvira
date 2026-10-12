"""Channels management REST endpoints with SQLite WAL persistence."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Query, Depends

from backend.config.models import (
    BulkInclusionPayload,
    BulkGroupPayload,
    BulkUserAgentPayload,
    BulkResetRewritesPayload,
    ChannelSearchPayload,
    ChannelRewritePayload,
    EPGMappingPayload,
    AutoMapEpgPayload,
    AutoMapEpgResponse,
)
from backend.services.channel_service import ChannelService

router = APIRouter()


def get_channel_service() -> ChannelService:
    """Dependency provider for ChannelService instance."""
    return ChannelService()


@router.post("/search", status_code=status.HTTP_200_OK)
def search_channels(
    payload: ChannelSearchPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, Any]:
    """Retrieves processed channels using JSON body filter criteria and pagination parameters.

    Args:
        payload (ChannelSearchPayload): Channel search and filter criteria payload.
        service (ChannelService): ChannelService dependency instance.

    Returns:
        Dict[str, Any]: Payload containing total count and filtered channels items.
    """
    return service.get_processed_channels(
        search=payload.search,
        source=payload.source,
        group=payload.group,
        is_included=payload.is_included,
        is_mapped=payload.is_mapped,
        link_status=payload.link_status,
        limit=payload.limit,
        offset=payload.offset,
    )


@router.get("", status_code=status.HTTP_200_OK)
def get_channels(
    search: Optional[str] = Query(None, description="Filter by channel name search query"),
    source: Optional[str] = Query(None, description="Filter by IPTV source provider name"),
    group: Optional[str] = Query(None, description="Filter by group-title"),
    is_included: Optional[bool] = Query(None, description="Filter by inclusion status"),
    is_mapped: Optional[bool] = Query(None, description="Filter by EPG mapping status"),
    link_status: Optional[str] = Query(None, description="Filter by stream link status (online, offline, unchecked)"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: ChannelService = Depends(get_channel_service),
) -> Dict[str, Any]:
    """Retrieves processed channels with optional search and filter parameters.

    Returns:
        Dict[str, Any]: Payload containing total count and filtered channels items.
    """
    return service.get_processed_channels(
        search=search,
        source=source,
        group=group,
        is_included=is_included,
        is_mapped=is_mapped,
        link_status=link_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{channel_id}", status_code=status.HTTP_200_OK)
def get_channel_by_id(
    channel_id: str, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, Any]:
    """Retrieves full details for a single channel by its unique ID.

    Args:
        channel_id (str): Unique channel MD5 hash identifier.
        service (ChannelService): ChannelService dependency instance.

    Returns:
        Dict[str, Any]: Channel details model.
    """
    return service._get_required_channel_by_id(channel_id)


@router.put("/{channel_id}/rewrite", status_code=status.HTTP_200_OK)
def update_channel_rewrite_by_id(
    channel_id: str,
    payload: ChannelRewritePayload,
    service: ChannelService = Depends(get_channel_service),
) -> Dict[str, str]:
    """Updates or removes an individual channel attribute rewrite rule by channel ID.

    Args:
        channel_id (str): Unique channel MD5 hash identifier.
        payload (ChannelRewritePayload): Target attribute rewrite details.
        service (ChannelService): ChannelService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.update_rewrite_by_channel_id(
        channel_id,
        field=payload.field,
        new_val=payload.new_val,
        original_url=payload.original_url,
        original_val=payload.original_val,
    )
    return {"message": f"Individual rewrite for field '{payload.field}' updated successfully."}


@router.put("/{channel_id}/epg-mapping", status_code=status.HTTP_200_OK)
def update_channel_epg_mapping_by_id(
    channel_id: str,
    payload: EPGMappingPayload,
    service: ChannelService = Depends(get_channel_service),
) -> Dict[str, str]:
    """Updates manual EPG mapping override by channel ID.

    Args:
        channel_id (str): Unique channel MD5 hash identifier.
        payload (EPGMappingPayload): EPG mapping override payload.
        service (ChannelService): ChannelService dependency instance.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.update_epg_mapping_by_channel_id(
        channel_id,
        epg_id=payload.epg_id,
        channel_name=payload.channel_name,
        source_name=payload.source_name,
        is_global=payload.is_global,
    )
    return {"message": f"EPG mapping override updated successfully."}


@router.put("/rewrite", status_code=status.HTTP_200_OK)
def update_channel_rewrite(
    payload: ChannelRewritePayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Updates or removes an individual channel attribute rewrite rule."""
    service.update_individual_rewrite(
        payload.original_url, payload.field, payload.original_val, payload.new_val
    )
    return {"message": f"Individual rewrite for field '{payload.field}' updated successfully."}


@router.put("/epg-mapping", status_code=status.HTTP_200_OK)
def update_channel_epg_mapping(
    payload: EPGMappingPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Updates manual EPG mapping override for a channel."""
    service.update_epg_mapping(payload.channel_name, payload.source_name, payload.epg_id, payload.is_global)
    return {"message": f"EPG mapping override for '{payload.channel_name}' updated successfully."}


@router.post("/bulk/inclusion", status_code=status.HTTP_200_OK)
def bulk_set_channel_inclusion(
    payload: BulkInclusionPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Sets channel inclusion/exclusion status in bulk for source settings."""
    count = service.bulk_set_inclusion(payload.channel_items, payload.is_included)
    return {"message": f"Bulk inclusion updated for {count} channels."}


@router.post("/bulk/group", status_code=status.HTTP_200_OK)
def bulk_set_channel_group(
    payload: BulkGroupPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Sets channel group in bulk via individual rewrite rules."""
    count = service.bulk_set_group(payload.original_urls, payload.group)
    return {"message": f"Bulk group set to '{payload.group}' for {count} channels."}


@router.post("/bulk/user-agent", status_code=status.HTTP_200_OK)
def bulk_set_channel_user_agent(
    payload: BulkUserAgentPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Sets channel User-Agent in bulk via individual rewrite rules."""
    count = service.bulk_set_user_agent(payload.original_urls, payload.user_agent)
    return {"message": f"Bulk User-Agent updated for {count} channels."}


@router.post("/bulk/reset-rewrites", status_code=status.HTTP_200_OK)
def bulk_reset_channel_rewrites(
    payload: BulkResetRewritesPayload, service: ChannelService = Depends(get_channel_service)
) -> Dict[str, str]:
    """Clears individual rewrite rules in bulk for target channel original_urls."""
    count = service.bulk_reset_rewrites(payload.original_urls)
    return {"message": f"Individual rewrites reset for {count} channels."}


@router.post(
    "/auto-map-epg",
    status_code=status.HTTP_200_OK,
    response_model=AutoMapEpgResponse,
    responses={
        403: {"description": "Catalog-wide auto-assign requires Pluvira Pro"},
    },
)
def auto_map_epg(
    payload: AutoMapEpgPayload,
    service: ChannelService = Depends(get_channel_service),
) -> AutoMapEpgResponse:
    """Automatically assigns EPG guides to channels enforcing Freemium BSL 1.1 limits.

    Args:
        payload (AutoMapEpgPayload): Mapping parameters and channel scope.
        service (ChannelService): ChannelService dependency instance.

    Returns:
        AutoMapEpgResponse: Mapping execution report and applied overrides.
    """
    result = service.auto_assign_epg(
        scope=payload.scope,
        playlist_id=payload.playlist_id,
        similarity_threshold=payload.similarity_threshold,
        overwrite_existing=payload.overwrite_existing,
        source=payload.source,
        only_unmapped=payload.only_unmapped if not payload.overwrite_existing else False,
    )
    return AutoMapEpgResponse(**result)
