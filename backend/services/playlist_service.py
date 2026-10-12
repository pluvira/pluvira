"""Playlist service layer encapsulating business logic for curated personal playlists."""

import secrets
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.config.models import PersonalPlaylist
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.config.settings import settings
from backend.core.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidConfigurationError,
)
from backend.core.license_thresholds import LicenseThresholdManager


class PlaylistService:
    """Service handling CRUD operations and export tokens for Curated Personal Playlists."""

    def __init__(self, repository: Optional[PersonalPlaylistRepository] = None) -> None:
        """Initializes playlist service and ensures SQLite schema is initialized.

        Args:
            repository (Optional[PersonalPlaylistRepository]): Override personal playlist repository.
        """
        self.repository = repository or PersonalPlaylistRepository(settings.data_dir)
        self.ensure_default_playlist()

    def ensure_default_playlist(self) -> None:
        """Ensures the default system playlist exists."""
        self.repository.ensure_default_playlist()

    def get_playlists(self) -> List[Dict[str, Any]]:
        """Retrieves all configured personal playlists.

        Returns:
            List[Dict[str, Any]]: List of personal playlist dictionaries.
        """
        return self.repository.get_playlists()

    def get_playlist_by_id(self, playlist_id: str) -> Dict[str, Any]:
        """Retrieves a single personal playlist by ID or slug.

        Args:
            playlist_id (str): Playlist unique identifier.

        Returns:
            Dict[str, Any]: Playlist dictionary.

        Raises:
            EntityNotFoundError: If playlist is not found.
        """
        playlist = self.repository.get_playlist_by_id(playlist_id)
        if not playlist:
            raise EntityNotFoundError(f"Playlist with ID '{playlist_id}' not found.")
        return playlist

    def create_playlist(self, payload: PersonalPlaylist) -> Dict[str, Any]:
        """Creates a new personal playlist enforcing BSL 1.1 thresholds.

        Args:
            payload (PersonalPlaylist): Playlist creation model.

        Returns:
            Dict[str, Any]: Created playlist dictionary.

        Raises:
            DuplicateEntityError: If playlist ID already exists.
        """
        current_playlists = self.get_playlists()
        LicenseThresholdManager.validate_playlist_count(len(current_playlists) + 1)

        if any(p["id"] == payload.id for p in current_playlists):
            raise DuplicateEntityError(f"Playlist with ID '{payload.id}' already exists.")

        token = payload.export_token or secrets.token_urlsafe(16)
        now_str = payload.created_at or datetime.now(timezone.utc).isoformat()

        self.repository.create_playlist(
            playlist_id=payload.id,
            name=payload.name,
            export_token=token,
            is_default=payload.is_default,
            created_at=now_str,
        )

        return {
            "id": payload.id,
            "name": payload.name,
            "export_token": token,
            "is_default": payload.is_default,
            "created_at": now_str,
        }

    def update_playlist(
        self, playlist_id: str, name: str, export_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates personal playlist metadata.

        Args:
            playlist_id (str): Playlist unique identifier.
            name (str): New playlist display name.
            export_token (Optional[str]): Updated export token.

        Returns:
            Dict[str, Any]: Updated playlist dictionary.
        """
        existing = self.get_playlist_by_id(playlist_id)
        new_token = export_token if export_token is not None else existing["export_token"]

        self.repository.update_playlist(playlist_id, name, new_token)
        return self.get_playlist_by_id(playlist_id)

    def regenerate_token(self, playlist_id: str) -> str:
        """Regenerates security export token for playlist.

        Args:
            playlist_id (str): Playlist unique identifier.

        Returns:
            str: Newly generated token string.
        """
        self.get_playlist_by_id(playlist_id)
        new_token = secrets.token_urlsafe(16)
        self.repository.update_export_token(playlist_id, new_token)
        return new_token

    def delete_playlist(self, playlist_id: str) -> None:
        """Deletes a custom personal playlist and its associated channels.

        Args:
            playlist_id (str): Playlist identifier to remove.

        Raises:
            InvalidConfigurationError: If user attempts to delete the default playlist.
        """
        playlist = self.get_playlist_by_id(playlist_id)
        if playlist["is_default"] or playlist_id == "default":
            raise InvalidConfigurationError("The default playlist cannot be deleted.")

        self.repository.delete_playlist(playlist_id)
