"""Repository for managing master channel merges and fallback chains in SQLite pluvira_main.db."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from backend.config.models import ChannelMerge, StreamRef
from backend.core.db import DatabaseManager
from backend.core.base_repository import BaseRepository


class ChannelMergeRepository(BaseRepository):
    """Encapsulates SQLite operations for master channel merges and fallback chains."""

    table_name = "channel_merges"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)
        conn = self.get_conn()
        conn.close()



    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes channel merge tables."""
        DatabaseManager.init_channel_merges_table(conn)


    def get_all(self) -> Dict[str, ChannelMerge]:
        """Retrieves all channel merges mapped by master_name.

        Returns:
            Dict[str, ChannelMerge]: Dictionary mapping master_name to ChannelMerge model.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT master_name, name, epg_id, logo, group_title, user_agent,
                       primary_url, primary_source, primary_user_agent
                FROM channel_merges
                ORDER BY master_name ASC
                """
            )
            master_rows = cursor.fetchall()
            if not master_rows:
                return {}

            cursor.execute(
                """
                SELECT master_name, url, source, user_agent
                FROM channel_merge_backups
                ORDER BY master_name ASC, priority ASC
                """
            )
            backup_rows = cursor.fetchall()
            backups_by_master: Dict[str, List[StreamRef]] = {}
            for m_name, url, source, ua in backup_rows:
                backups_by_master.setdefault(m_name, []).append(
                    StreamRef(url=url, source=source, user_agent=ua)
                )

            merges: Dict[str, ChannelMerge] = {}
            for row in master_rows:
                m_name, name, epg_id, logo, grp, ua, p_url, p_source, p_ua = row
                primary = StreamRef(url=p_url, source=p_source, user_agent=p_ua)
                backups = backups_by_master.get(m_name, [])
                merges[m_name] = ChannelMerge(
                    name=name or m_name,
                    epg_id=epg_id or "",
                    logo=logo or "",
                    group=grp or "",
                    user_agent=ua,
                    primary_stream=primary,
                    backup_streams=backups,
                )
            return merges
        finally:
            conn.close()

    def get_by_master_name(self, master_name: str) -> Optional[ChannelMerge]:
        """Retrieves a single channel merge by master_name.

        Args:
            master_name (str): Master channel identifier.

        Returns:
            Optional[ChannelMerge]: ChannelMerge model if found, None otherwise.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT master_name, name, epg_id, logo, group_title, user_agent,
                       primary_url, primary_source, primary_user_agent
                FROM channel_merges
                WHERE master_name = ?
                """,
                (master_name,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            m_name, name, epg_id, logo, grp, ua, p_url, p_source, p_ua = row
            cursor.execute(
                """
                SELECT url, source, user_agent
                FROM channel_merge_backups
                WHERE master_name = ?
                ORDER BY priority ASC
                """,
                (master_name,),
            )
            backups = [
                StreamRef(url=b_url, source=b_src, user_agent=b_ua)
                for b_url, b_src, b_ua in cursor.fetchall()
            ]

            return ChannelMerge(
                name=name or m_name,
                epg_id=epg_id or "",
                logo=logo or "",
                group=grp or "",
                user_agent=ua,
                primary_stream=StreamRef(url=p_url, source=p_source, user_agent=p_ua),
                backup_streams=backups,
            )
        finally:
            conn.close()

    def save_merge(self, merge: ChannelMerge, master_name: Optional[str] = None) -> None:
        """Saves or updates a channel merge and its fallback backup streams atomically.

        Args:
            merge (ChannelMerge): Channel merge model to persist.
            master_name (Optional[str]): Override master channel key (defaults to merge.name).
        """
        key = (master_name or merge.name or merge.primary_stream.url).strip()
        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO channel_merges (
                        master_name, name, epg_id, logo, group_title, user_agent,
                        primary_url, primary_source, primary_user_agent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(master_name) DO UPDATE SET
                        name = excluded.name,
                        epg_id = excluded.epg_id,
                        logo = excluded.logo,
                        group_title = excluded.group_title,
                        user_agent = excluded.user_agent,
                        primary_url = excluded.primary_url,
                        primary_source = excluded.primary_source,
                        primary_user_agent = excluded.primary_user_agent;
                    """,
                    (
                        key,
                        merge.name or key,
                        merge.epg_id or "",
                        merge.logo or "",
                        merge.group or "",
                        merge.user_agent,
                        merge.primary_stream.url,
                        merge.primary_stream.source,
                        merge.primary_stream.user_agent,
                    ),
                )

                conn.execute(
                    "DELETE FROM channel_merge_backups WHERE master_name = ?",
                    (key,),
                )

                for idx, backup in enumerate(merge.backup_streams):
                    conn.execute(
                        """
                        INSERT INTO channel_merge_backups (
                            master_name, priority, url, source, user_agent
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (key, idx, backup.url, backup.source, backup.user_agent),
                    )
        finally:
            conn.close()

    def delete_merge(self, master_name: str) -> bool:
        """Deletes a channel merge and all associated backup streams.

        Args:
            master_name (str): Master channel identifier.

        Returns:
            bool: True if merge was deleted, False if not found.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM channel_merges WHERE master_name = ?",
                    (master_name,),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def bulk_save_merges(self, merges: List[ChannelMerge]) -> int:
        """Persists multiple channel merges in a single atomic transaction.

        Args:
            merges (List[ChannelMerge]): List of channel merge models.

        Returns:
            int: Total count of saved merges.
        """
        if not merges:
            return 0

        conn = self.get_conn()
        try:
            with conn:
                for merge in merges:
                    key = (merge.name or merge.primary_stream.url).strip()
                    conn.execute(
                        """
                        INSERT INTO channel_merges (
                            master_name, name, epg_id, logo, group_title, user_agent,
                            primary_url, primary_source, primary_user_agent
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(master_name) DO UPDATE SET
                            name = excluded.name,
                            epg_id = excluded.epg_id,
                            logo = excluded.logo,
                            group_title = excluded.group_title,
                            user_agent = excluded.user_agent,
                            primary_url = excluded.primary_url,
                            primary_source = excluded.primary_source,
                            primary_user_agent = excluded.primary_user_agent;
                        """,
                        (
                            key,
                            merge.name or key,
                            merge.epg_id or "",
                            merge.logo or "",
                            merge.group or "",
                            merge.user_agent,
                            merge.primary_stream.url,
                            merge.primary_stream.source,
                            merge.primary_stream.user_agent,
                        ),
                    )
                    conn.execute(
                        "DELETE FROM channel_merge_backups WHERE master_name = ?",
                        (key,),
                    )
                    for idx, backup in enumerate(merge.backup_streams):
                        conn.execute(
                            """
                            INSERT INTO channel_merge_backups (
                                master_name, priority, url, source, user_agent
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (key, idx, backup.url, backup.source, backup.user_agent),
                        )
            return len(merges)
        finally:
            conn.close()

    def bulk_delete_merges(self, master_names: List[str]) -> int:
        """Deletes multiple channel merges in bulk.

        Args:
            master_names (List[str]): List of master channel identifiers.

        Returns:
            int: Number of merges deleted.
        """
        if not master_names:
            return 0

        conn = self.get_conn()
        try:
            placeholders = ",".join("?" for _ in master_names)
            with conn:
                cursor = conn.execute(
                    f"DELETE FROM channel_merges WHERE master_name IN ({placeholders})",
                    master_names,
                )
                return cursor.rowcount
        finally:
            conn.close()



