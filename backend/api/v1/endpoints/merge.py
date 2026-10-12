"""Channel merge and failover cluster REST endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Query, Depends

from backend.services.merge_service import MergeService
from backend.config.models import (
    StreamRef,
    ApplyMergePayload,
    AutoApplyMergePayload,
    MergeClusterSearchPayload,
    BulkDeleteMergePayload,
)
from backend.core.utils import ParamUtils

router = APIRouter()


def get_merge_service() -> MergeService:
    """Dependency provider for MergeService instance."""
    return MergeService()


@router.get("/clusters", status_code=status.HTTP_200_OK)
def get_duplicate_clusters(
    similarity_threshold: float = Query(0.80, ge=0.50, le=1.00, description="Fuzzy string similarity threshold"),
    service: MergeService = Depends(get_merge_service),
) -> List[Dict[str, Any]]:
    """Scans processed channels and returns duplicate candidate clusters.

    Args:
        similarity_threshold (float): Fuzzy similarity threshold (0.50 to 1.00).

    Returns:
        List[Dict[str, Any]]: List of cluster objects.
    """
    return service.get_duplicate_clusters(similarity_threshold=similarity_threshold)


@router.post("/clusters/search", status_code=status.HTTP_200_OK)
def search_duplicate_clusters(
    payload: MergeClusterSearchPayload, service: MergeService = Depends(get_merge_service)
) -> List[Dict[str, Any]]:
    """Scans processed channels and returns duplicate candidate clusters using JSON payload.

    Args:
        payload (MergeClusterSearchPayload): Search options payload.

    Returns:
        List[Dict[str, Any]]: List of cluster objects.
    """
    return service.get_duplicate_clusters(similarity_threshold=payload.similarity_threshold)


@router.post("/apply", status_code=status.HTTP_200_OK)
def apply_channel_merge(
    payload: ApplyMergePayload, service: MergeService = Depends(get_merge_service)
) -> Dict[str, str]:
    """Persists a new or updated ChannelMerge configuration in config.yaml.

    Args:
        payload (ApplyMergePayload): Channel merge request parameters.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.apply_channel_merge(
        master_name=payload.master_name,
        primary_stream=payload.primary_stream,
        backup_streams=payload.backup_streams,
        logo=payload.logo,
        group=payload.group,
        epg_id=payload.epg_id,
    )
    return {"message": f"Channel merge for '{payload.master_name}' applied successfully."}


@router.put("/{master_name}", status_code=status.HTTP_200_OK)
def put_channel_merge_by_name(
    master_name: str,
    payload: ApplyMergePayload,
    service: MergeService = Depends(get_merge_service),
) -> Dict[str, str]:
    """RESTful endpoint to create or update a ChannelMerge configuration by master channel name.

    Args:
        master_name (str): Master channel display name.
        payload (ApplyMergePayload): Channel merge request parameters.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.apply_channel_merge(
        master_name=master_name,
        primary_stream=payload.primary_stream,
        backup_streams=payload.backup_streams,
        logo=payload.logo,
        group=payload.group,
        epg_id=payload.epg_id,
    )
    return {"message": f"Channel merge for '{master_name}' applied successfully."}


@router.delete("/{master_name}", status_code=status.HTTP_200_OK)
def delete_channel_merge(
    master_name: str, service: MergeService = Depends(get_merge_service)
) -> Dict[str, str]:
    """Removes a ChannelMerge configuration from config.yaml.

    Args:
        master_name (str): Master channel name key to remove.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_channel_merge(master_name)
    return {"message": f"Channel merge for '{master_name}' deleted successfully."}



@router.post("/bulk/apply", status_code=status.HTTP_200_OK)
def bulk_apply_channel_merges(
    payload: List[ApplyMergePayload], service: MergeService = Depends(get_merge_service)
) -> Dict[str, Any]:
    """Bulk application of channel merges for N clusters in a single atomic operation.

    Args:
        payload (List[ApplyMergePayload]): List of channel merge payloads.

    Returns:
        Dict[str, Any]: Operation status message and count.
    """
    items_dict = [p.model_dump() for p in payload]
    return service.bulk_apply_channel_merges(items_dict)


@router.post("/bulk/delete", status_code=status.HTTP_200_OK)
def bulk_delete_channel_merges(
    payload: BulkDeleteMergePayload, service: MergeService = Depends(get_merge_service)
) -> Dict[str, Any]:
    """Bulk deletion of channel merges to restore separate channels.

    Args:
        payload (BulkDeleteMergePayload): List of master channel names to unmerge.

    Returns:
        Dict[str, Any]: Operation status message and count.
    """
    return service.bulk_delete_channel_merges(payload.master_names)



@router.post("/auto-apply", status_code=status.HTTP_200_OK)
def auto_apply_channel_merges(
    payload: Optional[AutoApplyMergePayload] = None,
    similarity_threshold: Optional[float] = Query(None, ge=0.50, le=1.00, description="High-confidence fuzzy similarity threshold"),
    service: MergeService = Depends(get_merge_service),
) -> Dict[str, Any]:
    """Server-side auto-merge of duplicate candidate clusters exceeding similarity threshold.

    Args:
        payload (Optional[AutoApplyMergePayload]): Auto-merge payload options.
        similarity_threshold (Optional[float]): Legacy query parameter.

    Returns:
        Dict[str, Any]: Operation status message and merged count.
    """
    threshold = ParamUtils.resolve_param(
        payload.similarity_threshold if payload else None, similarity_threshold, 0.95
    )
    return service.auto_apply_channel_merges(similarity_threshold=threshold)



@router.get("/stats", status_code=status.HTTP_200_OK)
def get_merge_stats(
    similarity_threshold: float = Query(0.80, ge=0.50, le=1.00, description="Fuzzy string similarity threshold"),
    service: MergeService = Depends(get_merge_service),
) -> Dict[str, Any]:
    """Retrieves aggregate dashboard metrics for channel merge and failover clusters.

    Args:
        similarity_threshold (float): Fuzzy similarity threshold.

    Returns:
        Dict[str, Any]: Aggregate metrics payload.
    """
    return service.get_merge_stats(similarity_threshold=similarity_threshold)
