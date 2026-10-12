"""Personal channels, slot pool management, and suggestions REST API endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Query, Depends

from backend.config.models import (
    PersonalChannel,
    ChannelSlot,
    BookmarkPayload,
    ChannelUpdatePayload,
    SlotReorderPayload,
    PurgePayload,
)
from backend.services.personal_channel_service import PersonalChannelService
from backend.services.purge_service import PurgeService

router = APIRouter()


def get_personal_channel_service() -> PersonalChannelService:
    """Dependency provider for PersonalChannelService instance."""
    return PersonalChannelService()


def get_purge_service() -> PurgeService:
    """Dependency provider for PurgeService instance."""
    return PurgeService()


@router.get("", status_code=status.HTTP_200_OK)
def get_personal_channels(
    playlist_id: str = Query("default", description="Filter channels by playlist identifier"),
    service: PersonalChannelService = Depends(get_personal_channel_service),
) -> List[Dict[str, Any]]:
    """Retrieves all personal channels with slots and suggestions for target playlist.

    Args:
        playlist_id (str): Target playlist identifier.

    Returns:
        List[Dict[str, Any]]: List of personal channel objects.
    """
    return service.get_channels(playlist_id=playlist_id)


@router.get("/{channel_id}", status_code=status.HTTP_200_OK)
def get_personal_channel_by_id(
    channel_id: str, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, Any]:
    """Retrieves details of a single personal channel.

    Args:
        channel_id (str): Channel unique identifier.

    Returns:
        Dict[str, Any]: Personal channel object.
    """
    return service.get_channel_by_id(channel_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={403: {"description": "Personal channel limit exceeded (max 25 in Free Tier)"}},
)
def create_personal_channel(
    payload: PersonalChannel, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, Any]:
    """Creates a new logical personal channel.

    Args:
        payload (PersonalChannel): Channel model payload.

    Returns:
        Dict[str, Any]: Created personal channel object.
    """
    return service.create_channel(payload)


@router.put("/{channel_id}", status_code=status.HTTP_200_OK)
def update_personal_channel(
    channel_id: str,
    payload: ChannelUpdatePayload,
    service: PersonalChannelService = Depends(get_personal_channel_service),
) -> Dict[str, Any]:
    """Updates metadata of a personal channel.

    Args:
        channel_id (str): Channel unique identifier.
        payload (ChannelUpdatePayload): Fields to update.

    Returns:
        Dict[str, Any]: Updated channel object.
    """
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return service.update_channel(channel_id, updates)


@router.delete("/{channel_id}", status_code=status.HTTP_200_OK)
def delete_personal_channel(
    channel_id: str, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, str]:
    """Deletes a personal channel and all its stream slots.

    Args:
        channel_id (str): Channel unique identifier.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_channel(channel_id)
    return {"message": f"Personal channel '{channel_id}' deleted successfully."}


@router.post(
    "/bookmark",
    status_code=status.HTTP_200_OK,
    responses={403: {"description": "Personal channel limit exceeded (max 25 in Free Tier)"}},
)
def toggle_channel_bookmark(
    payload: BookmarkPayload, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, Any]:
    """Toggles bookmark (star/unstar) for a catalog channel in target playlist.

    Args:
        payload (BookmarkPayload): Target playlist and catalog channel.

    Returns:
        Dict[str, Any]: Bookmark status report.
    """
    return service.toggle_bookmark(payload.playlist_id, payload.channel)


@router.post(
    "/{channel_id}/slots",
    status_code=status.HTTP_200_OK,
    responses={403: {"description": "Stream slot limit exceeded (max 2 in Free Tier, 7 in Pro)"}},
)
def add_stream_slot(
    channel_id: str,
    slot: ChannelSlot,
    service: PersonalChannelService = Depends(get_personal_channel_service),
) -> Dict[str, Any]:
    """Adds a physical stream slot to a personal channel enforcing 7-slot cap.

    Args:
        channel_id (str): Target channel identifier.
        slot (ChannelSlot): Stream slot payload.

    Returns:
        Dict[str, Any]: Updated personal channel object.
    """
    return service.add_slot(channel_id, slot)


@router.delete("/{channel_id}/slots/{slot_id}", status_code=status.HTTP_200_OK)
def remove_stream_slot(
    channel_id: str,
    slot_id: str,
    service: PersonalChannelService = Depends(get_personal_channel_service),
) -> Dict[str, Any]:
    """Removes a stream slot from a personal channel.

    Args:
        channel_id (str): Target channel identifier.
        slot_id (str): Target slot identifier.

    Returns:
        Dict[str, Any]: Updated personal channel object.
    """
    return service.remove_slot(channel_id, slot_id)


@router.post("/{channel_id}/slots/reorder", status_code=status.HTTP_200_OK)
def reorder_stream_slots(
    channel_id: str,
    payload: SlotReorderPayload,
    service: PersonalChannelService = Depends(get_personal_channel_service),
) -> Dict[str, Any]:
    """Manually reorders stream slots in a personal channel.

    Args:
        channel_id (str): Target channel identifier.
        payload (SlotReorderPayload): Ordered list of slot IDs.

    Returns:
        Dict[str, Any]: Updated personal channel object.
    """
    return service.reorder_slots_manual(channel_id, payload.slot_ids)


@router.post("/suggestions/{suggestion_id}/approve", status_code=status.HTTP_200_OK)
def approve_stream_suggestion(
    suggestion_id: str, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, Any]:
    """Approves a candidate suggestion and attaches it to the target personal channel slot pool.

    Args:
        suggestion_id (str): Target suggestion identifier.

    Returns:
        Dict[str, Any]: Updated personal channel object.
    """
    return service.approve_suggestion(suggestion_id)


@router.post("/suggestions/{suggestion_id}/reject", status_code=status.HTTP_200_OK)
def reject_stream_suggestion(
    suggestion_id: str, service: PersonalChannelService = Depends(get_personal_channel_service)
) -> Dict[str, str]:
    """Rejects and dismisses a candidate stream suggestion.

    Args:
        suggestion_id (str): Target suggestion identifier.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.reject_suggestion(suggestion_id)
    return {"message": f"Suggestion '{suggestion_id}' rejected successfully."}


@router.post("/purge-quarantined", status_code=status.HTTP_200_OK)
def purge_quarantined_streams(
    payload: Optional[PurgePayload] = None, service: PurgeService = Depends(get_purge_service)
) -> Dict[str, Any]:
    """Manually purges all quarantined stream slots.

    Args:
        payload (Optional[PurgePayload]): Optional playlist filter.

    Returns:
        Dict[str, Any]: Purged streams count report.
    """
    pl_id = payload.playlist_id if payload else None
    res = service.purge_quarantined_streams(playlist_id=pl_id)
    return {"message": f"Purged {res['purged_count']} quarantined stream(s).", **res}
