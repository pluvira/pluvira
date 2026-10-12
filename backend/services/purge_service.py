"""Purge service layer encapsulating manual and scheduled automatic cleanup of quarantined streams."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.config.settings import settings


class PurgeService:
    """Service handling manual one-click purge and scheduled expiration purge for quarantined stream slots."""

    def __init__(self, repository: Optional[PersonalPlaylistRepository] = None) -> None:
        """Initializes purge service and ensures schema exists.

        Args:
            repository (Optional[PersonalPlaylistRepository]): Override personal playlist repository.
        """
        self.repository = repository or PersonalPlaylistRepository(settings.data_dir)

    def purge_quarantined_streams(self, playlist_id: Optional[str] = None) -> Dict[str, int]:
        """Manually deletes all quarantined stream slots across playlists or for a specific playlist.

        Args:
            playlist_id (Optional[str]): Optional filter by personal playlist identifier.

        Returns:
            Dict[str, int]: Purged stream slots count summary.
        """
        purged_count = self.repository.purge_quarantined_slots(playlist_id)
        return {"purged_count": max(0, purged_count)}

    def auto_purge_expired_streams(self, days_threshold: int = 7) -> Dict[str, int]:
        """Automatically purges quarantined streams that have exceeded the retention days threshold.

        Args:
            days_threshold (int): Max retention days in quarantine before definitive purge.

        Returns:
            Dict[str, int]: Purged streams count summary.
        """
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        cutoff_str = cutoff_dt.isoformat()

        purged_count = self.repository.purge_expired_quarantined_slots(cutoff_str)
        logging.info(f"Auto-purge completed: removed {purged_count} expired quarantined streams.")
        return {"purged_count": max(0, purged_count)}
