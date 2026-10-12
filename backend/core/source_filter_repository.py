"""Repository for managing source-specific channel filters (allow/deny) in SQLite pluvira_main.db."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from backend.core.db import DatabaseManager
from backend.core.base_repository import BaseRepository


class SourceFilterRepository(BaseRepository):
    """Encapsulates SQLite operations for source channel filters (allow and deny lists)."""

    table_name = "source_channel_filters"

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes source channel filters table and indexes."""
        DatabaseManager.init_source_channel_filters_table(conn)

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)





    def get_all_grouped(self) -> Dict[str, Dict[str, Set[str]]]:
        """Retrieves all filters grouped by source_name and filter_type.

        Returns:
            Dict[str, Dict[str, Set[str]]]: Map of source_name -> {'allow': Set[str], 'deny': Set[str]}.
        """
        conn = self.get_conn()
        grouped: Dict[str, Dict[str, Set[str]]] = {}
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_name, channel_name, filter_type
                FROM source_channel_filters
                ORDER BY source_name ASC, channel_name ASC;
                """
            )
            for src_name, ch_name, f_type in cursor.fetchall():
                if src_name not in grouped:
                    grouped[src_name] = {"allow": set(), "deny": set()}
                grouped[src_name][f_type].add(ch_name)
            return grouped
        finally:
            conn.close()

    def get_filters_for_source(self, source_name: str) -> Tuple[Set[str], Set[str]]:
        """Retrieves allow and deny sets for a specific source.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            Tuple[Set[str], Set[str]]: Tuple of (allow_set, deny_set).
        """
        conn = self.get_conn()
        allow_set: Set[str] = set()
        deny_set: Set[str] = set()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT channel_name, filter_type
                FROM source_channel_filters
                WHERE source_name = ?;
                """,
                (source_name,),
            )
            for ch_name, f_type in cursor.fetchall():
                if f_type == "allow":
                    allow_set.add(ch_name)
                elif f_type == "deny":
                    deny_set.add(ch_name)
            return allow_set, deny_set
        finally:
            conn.close()

    def get_allowed_channels(self, source_name: str) -> Set[str]:
        """Retrieves allowed channel names for a source."""
        allow_set, _ = self.get_filters_for_source(source_name)
        return allow_set

    def get_denied_channels(self, source_name: str) -> Set[str]:
        """Retrieves denied channel names for a source."""
        _, deny_set = self.get_filters_for_source(source_name)
        return deny_set

    def set_filter(self, source_name: str, channel_name: str, filter_type: str) -> None:
        """Inserts or updates a filter for a channel in a source, enforcing mutual exclusivity.

        Args:
            source_name (str): IPTV source provider name.
            channel_name (str): Target channel name.
            filter_type (str): 'allow' or 'deny'.
        """
        if filter_type not in ("allow", "deny"):
            raise ValueError(f"Invalid filter_type '{filter_type}'. Must be 'allow' or 'deny'.")

        opposite_type = "deny" if filter_type == "allow" else "allow"
        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    DELETE FROM source_channel_filters
                    WHERE source_name = ? AND channel_name = ? AND filter_type = ?;
                    """,
                    (source_name, channel_name, opposite_type),
                )
                conn.execute(
                    """
                    INSERT INTO source_channel_filters (source_name, channel_name, filter_type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_name, channel_name, filter_type) DO NOTHING;
                    """,
                    (source_name, channel_name, filter_type),
                )
        finally:
            conn.close()

    def remove_filter(self, source_name: str, channel_name: str, filter_type: str) -> bool:
        """Removes a channel filter.

        Args:
            source_name (str): IPTV source provider name.
            channel_name (str): Target channel name.
            filter_type (str): 'allow' or 'deny'.

        Returns:
            bool: True if deleted, False if not found.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    DELETE FROM source_channel_filters
                    WHERE source_name = ? AND channel_name = ? AND filter_type = ?;
                    """,
                    (source_name, channel_name, filter_type),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def bulk_set_filters(self, source_name: str, channel_names: List[str], filter_type: str) -> int:
        """Bulk sets channel filters for a source enforcing mutual exclusivity.

        Args:
            source_name (str): IPTV source provider name.
            channel_names (List[str]): List of channel names.
            filter_type (str): 'allow' or 'deny'.

        Returns:
            int: Number of channel filters set.
        """
        if not channel_names:
            return 0
        if filter_type not in ("allow", "deny"):
            raise ValueError(f"Invalid filter_type '{filter_type}'. Must be 'allow' or 'deny'.")

        opposite_type = "deny" if filter_type == "allow" else "allow"
        conn = self.get_conn()
        try:
            with conn:
                del_params = [(source_name, ch, opposite_type) for ch in channel_names]
                conn.executemany(
                    """
                    DELETE FROM source_channel_filters
                    WHERE source_name = ? AND channel_name = ? AND filter_type = ?;
                    """,
                    del_params,
                )
                ins_params = [(source_name, ch, filter_type) for ch in channel_names]
                conn.executemany(
                    """
                    INSERT INTO source_channel_filters (source_name, channel_name, filter_type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_name, channel_name, filter_type) DO NOTHING;
                    """,
                    ins_params,
                )
            return len(channel_names)
        finally:
            conn.close()

    def bulk_remove_filters(self, source_name: str, channel_names: List[str], filter_type: str) -> int:
        """Bulk removes channel filters for a source.

        Args:
            source_name (str): IPTV source provider name.
            channel_names (List[str]): List of channel names.
            filter_type (str): 'allow' or 'deny'.

        Returns:
            int: Total rows deleted.
        """
        if not channel_names:
            return 0
        conn = self.get_conn()
        try:
            with conn:
                params = [(source_name, ch, filter_type) for ch in channel_names]
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    DELETE FROM source_channel_filters
                    WHERE source_name = ? AND channel_name = ? AND filter_type = ?;
                    """,
                    params,
                )
                return cursor.rowcount
        finally:
            conn.close()

    def delete_by_source(self, source_name: str) -> int:
        """Deletes all filters associated with a specific source.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            int: Total rows deleted.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    DELETE FROM source_channel_filters
                    WHERE source_name = ?;
                    """,
                    (source_name,),
                )
                return cursor.rowcount
        finally:
            conn.close()

    def bulk_set_all(self, items: List[Dict[str, Any]]) -> int:
        """Bulk inserts or replaces filter records from raw dictionary items.

        Args:
            items (List[Dict[str, Any]]): List of dicts with keys (source_name, channel_name, filter_type).

        Returns:
            int: Number of items processed.
        """
        if not items:
            return 0
        conn = self.get_conn()
        try:
            with conn:
                params = [
                    (item["source_name"], item["channel_name"], item["filter_type"])
                    for item in items
                    if item.get("source_name") and item.get("channel_name") and item.get("filter_type") in ("allow", "deny")
                ]
                conn.executemany(
                    """
                    INSERT INTO source_channel_filters (source_name, channel_name, filter_type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_name, channel_name, filter_type) DO NOTHING;
                    """,
                    params,
                )
            return len(params)
        finally:
            conn.close()

    def get_all_flat(self) -> List[Dict[str, Any]]:
        """Retrieves all source channel filters as a flat list of dictionaries for backup export.

        Returns:
            List[Dict[str, Any]]: List of filter dictionaries.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_name, channel_name, filter_type
                FROM source_channel_filters
                ORDER BY source_name ASC, filter_type ASC, channel_name ASC;
                """
            )
            return [
                {"source_name": row[0], "channel_name": row[1], "filter_type": row[2]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()



