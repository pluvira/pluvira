"""Repository for managing manual channel-to-EPG mapping overrides in SQLite pluvira_main.db."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from backend.core.db import DatabaseManager
from backend.core.base_repository import BaseRepository


class EpgOverrideRepository(BaseRepository):
    """Encapsulates SQLite operations for global and source-specific EPG mapping overrides."""

    table_name = "epg_mapping_overrides"

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes EPG mapping overrides table and indexes."""
        DatabaseManager.init_epg_overrides_table(conn)

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)





    def get_all_grouped(self) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
        """Retrieves all overrides partitioned into global map and per-source map.

        Returns:
            Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
                Tuple of (global_overrides, source_overrides_by_source).
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_name, epg_id, source_name FROM epg_mapping_overrides ORDER BY id ASC"
            )
            global_overrides: Dict[str, str] = {}
            source_overrides: Dict[str, Dict[str, str]] = {}

            for ch_name, epg_id, src_name in cursor.fetchall():
                src_clean = (src_name or "").strip()
                if not src_clean:
                    global_overrides[ch_name] = epg_id
                else:
                    source_overrides.setdefault(src_clean, {})[ch_name] = epg_id

            return global_overrides, source_overrides
        finally:
            conn.close()

    def get_global_overrides(self) -> Dict[str, str]:
        """Retrieves dictionary of global EPG mapping overrides.

        Returns:
            Dict[str, str]: Map of channel_name to namespaced epg_id.
        """
        global_map, _ = self.get_all_grouped()
        return global_map

    def get_source_overrides(self, source_name: str) -> Dict[str, str]:
        """Retrieves dictionary of EPG mapping overrides for a specific source provider.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            Dict[str, str]: Map of channel_name to namespaced epg_id.
        """
        _, src_map = self.get_all_grouped()
        return src_map.get(source_name.strip(), {})

    def set_override(
        self, channel_name: str, epg_id: str, source_name: Optional[str] = None
    ) -> None:
        """Inserts or updates an EPG mapping override for a channel.

        Args:
            channel_name (str): Target channel display name.
            epg_id (str): Namespaced EPG channel ID.
            source_name (Optional[str]): Source name if source-specific, or None for global.
        """
        src_clean = (source_name or "").strip()
        ch_clean = channel_name.strip()
        epg_clean = epg_id.strip()

        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO epg_mapping_overrides (channel_name, epg_id, source_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(channel_name, source_name) DO UPDATE SET
                        epg_id = excluded.epg_id,
                        created_at = CURRENT_TIMESTAMP;
                    """,
                    (ch_clean, epg_clean, src_clean),
                )
        finally:
            conn.close()

    def delete_override(
        self, channel_name: str, source_name: Optional[str] = None
    ) -> bool:
        """Deletes a specific EPG mapping override.

        Args:
            channel_name (str): Target channel display name.
            source_name (Optional[str]): Source name if source-specific, or None for global.

        Returns:
            bool: True if a record was deleted, False otherwise.
        """
        src_clean = (source_name or "").strip()
        ch_clean = channel_name.strip()

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM epg_mapping_overrides WHERE channel_name = ? AND source_name = ?",
                    (ch_clean, src_clean),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_by_source(self, source_name: str) -> int:
        """Deletes all overrides associated with a specific source provider.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            int: Number of deleted override records.
        """
        src_clean = source_name.strip()
        if not src_clean:
            return 0

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM epg_mapping_overrides WHERE source_name = ?",
                    (src_clean,),
                )
                return cursor.rowcount
        finally:
            conn.close()

    def bulk_set_overrides(self, items: List[Dict[str, Any]]) -> int:
        """Saves multiple EPG mapping overrides in a single atomic transaction.

        Args:
            items (List[Dict[str, Any]]): List of dicts containing channel_name, epg_id, source_name.

        Returns:
            int: Count of overrides inserted/updated.
        """
        if not items:
            return 0

        conn = self.get_conn()
        try:
            with conn:
                for item in items:
                    ch = item.get("channel_name", "").strip()
                    epg = item.get("epg_id", "").strip()
                    src = (item.get("source_name") or "").strip()
                    if ch and epg:
                        conn.execute(
                            """
                            INSERT INTO epg_mapping_overrides (channel_name, epg_id, source_name)
                            VALUES (?, ?, ?)
                            ON CONFLICT(channel_name, source_name) DO UPDATE SET
                                epg_id = excluded.epg_id,
                                created_at = CURRENT_TIMESTAMP;
                            """,
                            (ch, epg, src),
                        )
            return len(items)
        finally:
            conn.close()



