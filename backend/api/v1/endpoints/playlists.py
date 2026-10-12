"""Curated personal playlists REST API endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Depends

from backend.config.models import PersonalPlaylist, PlaylistUpdatePayload
from backend.services.playlist_service import PlaylistService

router = APIRouter()


def get_playlist_service() -> PlaylistService:
    """Dependency provider for PlaylistService instance."""
    return PlaylistService()


@router.get("", status_code=status.HTTP_200_OK)
def get_playlists(service: PlaylistService = Depends(get_playlist_service)) -> List[Dict[str, Any]]:
    """Retrieves list of all configured curated personal playlists.

    Returns:
        List[Dict[str, Any]]: List of personal playlist objects.
    """
    return service.get_playlists()


@router.get("/{playlist_id}", status_code=status.HTTP_200_OK)
def get_playlist_by_id(
    playlist_id: str, service: PlaylistService = Depends(get_playlist_service)
) -> Dict[str, Any]:
    """Retrieves details of a single personal playlist.

    Args:
        playlist_id (str): Playlist unique identifier.

    Returns:
        Dict[str, Any]: Personal playlist object.
    """
    return service.get_playlist_by_id(playlist_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PersonalPlaylist, service: PlaylistService = Depends(get_playlist_service)
) -> Dict[str, Any]:
    """Creates a new curated personal playlist enforcing BSL 1.1 thresholds.

    Args:
        payload (PersonalPlaylist): Playlist creation model.

    Returns:
        Dict[str, Any]: Created playlist object.
    """
    return service.create_playlist(payload)


@router.put("/{playlist_id}", status_code=status.HTTP_200_OK)
def update_playlist(
    playlist_id: str,
    payload: PlaylistUpdatePayload,
    service: PlaylistService = Depends(get_playlist_service),
) -> Dict[str, Any]:
    """Updates display name or export token of a personal playlist.

    Args:
        playlist_id (str): Target playlist identifier.
        payload (PlaylistUpdatePayload): Updated fields.

    Returns:
        Dict[str, Any]: Updated playlist object.
    """
    return service.update_playlist(playlist_id, name=payload.name, export_token=payload.export_token)


@router.delete("/{playlist_id}", status_code=status.HTTP_200_OK)
def delete_playlist(
    playlist_id: str, service: PlaylistService = Depends(get_playlist_service)
) -> Dict[str, str]:
    """Deletes a custom personal playlist.

    Args:
        playlist_id (str): Target playlist identifier.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_playlist(playlist_id)
    return {"message": f"Playlist '{playlist_id}' deleted successfully."}


@router.post("/{playlist_id}/regenerate-token", status_code=status.HTTP_200_OK)
def regenerate_playlist_token(
    playlist_id: str, service: PlaylistService = Depends(get_playlist_service)
) -> Dict[str, str]:
    """Regenerates the secret security export token for a playlist.

    Args:
        playlist_id (str): Target playlist identifier.

    Returns:
        Dict[str, str]: New export token response.
    """
    token = service.regenerate_token(playlist_id)
    return {"token": token, "message": "Export token regenerated successfully."}
