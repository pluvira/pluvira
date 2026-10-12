"""Repository for managing system broadcast bulletins in SQLite pluvira_main.db."""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Any, Union, Dict

from backend.config.models import BulletinDTO, BulletinMediaDTO, BulletinAckPayload
from backend.core.base_repository import BaseRepository
from backend.core.db import db_manager


class BulletinRepository(BaseRepository):
    """Encapsulates SQLite operations for system broadcast bulletins in pluvira_main.db."""

    table_name = "system_bulletins"
    db_type = "main"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path, table_name="system_bulletins", db_type="main")

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes system_bulletins table and indexes."""
        db_manager.init_bulletin_tables(conn)

    def upsert_bulletins(self, bulletins: List[BulletinDTO]) -> int:
        """Inserts or updates bulletins preserving existing is_dismissed status.

        Args:
            bulletins (List[BulletinDTO]): Incoming bulletin DTOs.

        Returns:
            int: Number of upserted bulletins.
        """
        if not bulletins:
            return 0

        conn = self.get_conn()
        count = 0
        with conn:
            for b in bulletins:
                media_json = json.dumps(b.media.model_dump()) if b.media else None
                conn.execute(
                    """
                    INSERT INTO system_bulletins (
                        id, level, icon, title_json, message_json, action_label_json,
                        action_url, media_json, dismissible, priority, expires_at, signature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        level = excluded.level,
                        icon = excluded.icon,
                        title_json = excluded.title_json,
                        message_json = excluded.message_json,
                        action_label_json = excluded.action_label_json,
                        action_url = excluded.action_url,
                        media_json = excluded.media_json,
                        dismissible = excluded.dismissible,
                        priority = excluded.priority,
                        expires_at = excluded.expires_at,
                        signature = excluded.signature;
                    """,
                    (
                        b.id,
                        b.level,
                        b.icon,
                        json.dumps(b.title),
                        json.dumps(b.message),
                        json.dumps(b.action_label) if b.action_label else None,
                        b.action_url,
                        media_json,
                        1 if b.dismissible else 0,
                        b.priority,
                        b.expires_at,
                        b.signature,
                    ),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bulletin_sync_queue (bulletin_id, event_type)
                    VALUES (?, 'received');
                    """,
                    (b.id,),
                )
                count += 1
        return count

    def get_active_bulletins(self, include_dismissed: bool = False) -> List[BulletinDTO]:
        """Retrieves unexpired bulletins sorted by priority and received timestamp.

        Args:
            include_dismissed (bool): Whether to include dismissed bulletins.

        Returns:
            List[BulletinDTO]: List of active bulletin DTOs.
        """
        now_ts = int(datetime.now(timezone.utc).timestamp())
        conn = self.get_conn()
        cursor = conn.cursor()
        query = """
            SELECT id, level, icon, title_json, message_json, action_label_json,
                   action_url, media_json, dismissible, priority, expires_at,
                   signature, is_dismissed, dismissed_at, is_read, read_at
            FROM system_bulletins
            WHERE expires_at > ?
        """
        params: List[Any] = [now_ts]
        if not include_dismissed:
            query += " AND is_dismissed = 0"
        query += " ORDER BY priority DESC, received_at DESC;"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result: List[BulletinDTO] = []
        for r in rows:
            media_dto = None
            if r[7]:
                try:
                    media_dto = BulletinMediaDTO(**json.loads(r[7]))
                except Exception:
                    pass
            action_label = None
            if r[5]:
                try:
                    action_label = json.loads(r[5])
                except Exception:
                    pass
            try:
                dto = BulletinDTO(
                    id=r[0],
                    level=r[1],
                    icon=r[2],
                    title=json.loads(r[3]),
                    message=json.loads(r[4]),
                    action_label=action_label,
                    action_url=r[6],
                    media=media_dto,
                    dismissible=bool(r[8]),
                    priority=r[9],
                    expires_at=r[10],
                    signature=r[11],
                    is_dismissed=bool(r[12]),
                    dismissed_at=r[13],
                    is_read=bool(r[14]),
                    read_at=r[15],
                )
                result.append(dto)
            except Exception as e:
                logging.warning(f"Error deserializing bulletin {r[0]}: {e}")
        return result

    def dismiss_bulletin(self, bulletin_id: str) -> bool:
        """Marks a bulletin as dismissed with an ISO timestamp and enqueues dismissal event.

        Args:
            bulletin_id (str): Target bulletin identifier.

        Returns:
            bool: True if record was updated, False otherwise.
        """
        conn = self.get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute(
                """
                UPDATE system_bulletins
                SET is_dismissed = 1, dismissed_at = ?
                WHERE id = ?;
                """,
                (now_iso, bulletin_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bulletin_sync_queue (bulletin_id, event_type)
                    VALUES (?, 'dismissed');
                    """,
                    (bulletin_id,),
                )
            return updated

    def mark_read(self, bulletin_id: str) -> bool:
        """Marks a bulletin as read with an ISO timestamp and enqueues read receipt.

        Args:
            bulletin_id (str): Target bulletin identifier.

        Returns:
            bool: True if record was updated, False otherwise.
        """
        conn = self.get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute(
                """
                UPDATE system_bulletins
                SET is_read = 1, read_at = ?
                WHERE id = ?;
                """,
                (now_iso, bulletin_id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bulletin_sync_queue (bulletin_id, event_type)
                    VALUES (?, 'read');
                    """,
                    (bulletin_id,),
                )
            return updated

    def queue_event(self, bulletin_id: str, event_type: str) -> bool:
        """Enqueues a lifecycle acknowledgment event for subsequent heartbeat reporting.

        Args:
            bulletin_id (str): Target bulletin identifier.
            event_type (str): Event type ('received', 'read', 'dismissed').

        Returns:
            bool: True if queued, False on invalid type or error.
        """
        if event_type not in ("received", "read", "dismissed"):
            return False
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO bulletin_sync_queue (bulletin_id, event_type)
                VALUES (?, ?);
                """,
                (bulletin_id, event_type),
            )
            return cursor.rowcount > 0

    def get_pending_events(self) -> BulletinAckPayload:
        """Retrieves all pending lifecycle events grouped by event type.

        Returns:
            BulletinAckPayload: Grouped lists of bulletin IDs.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT bulletin_id, event_type FROM bulletin_sync_queue ORDER BY queued_at ASC;")
        rows = cursor.fetchall()
        received: List[str] = []
        read: List[str] = []
        dismissed: List[str] = []
        for b_id, evt in rows:
            if evt == "received":
                received.append(b_id)
            elif evt == "read":
                read.append(b_id)
            elif evt == "dismissed":
                dismissed.append(b_id)
        return BulletinAckPayload(received=received, read=read, dismissed=dismissed)

    def pop_and_drain_events(
        self,
        events: Optional[Union[BulletinAckPayload, Dict[str, List[str]], List[tuple[str, str]]]] = None,
    ) -> int:
        """Drains specified or all confirmed lifecycle acknowledgment events from the queue.

        Args:
            events (Optional[Union[BulletinAckPayload, Dict[str, List[str]], List[tuple[str, str]]]]):
                Specific events confirmed by SaaS or None to drain all.

        Returns:
            int: Number of deleted queue records.
        """
        conn = self.get_conn()
        with conn:
            if events is None:
                cursor = conn.execute("DELETE FROM bulletin_sync_queue;")
                return cursor.rowcount

            pairs: List[tuple[str, str]] = []
            if isinstance(events, BulletinAckPayload):
                for b_id in events.received:
                    pairs.append((b_id, "received"))
                for b_id in events.read:
                    pairs.append((b_id, "read"))
                for b_id in events.dismissed:
                    pairs.append((b_id, "dismissed"))
            elif isinstance(events, dict):
                for evt_type, id_list in events.items():
                    if isinstance(id_list, list):
                        for b_id in id_list:
                            pairs.append((str(b_id), str(evt_type)))
            elif isinstance(events, list):
                for item in events:
                    if isinstance(item, (tuple, list)) and len(item) == 2:
                        pairs.append((item[0], item[1]))

            if not pairs:
                return 0

            cursor = conn.executemany(
                "DELETE FROM bulletin_sync_queue WHERE bulletin_id = ? AND event_type = ?;",
                pairs,
            )
            return cursor.rowcount

    def prune_expired(self) -> int:
        """Removes bulletins whose expiration timestamp has passed.

        Returns:
            int: Number of deleted rows.
        """
        now_ts = int(datetime.now(timezone.utc).timestamp())
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                "DELETE FROM system_bulletins WHERE expires_at <= ?;",
                (now_ts,),
            )
            return cursor.rowcount

    def delete_bulletin(self, bulletin_id: str) -> bool:
        """Permanently deletes a bulletin by ID from storage.

        Args:
            bulletin_id (str): Target bulletin identifier.

        Returns:
            bool: True if record was deleted, False otherwise.
        """
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                "DELETE FROM system_bulletins WHERE id = ?;",
                (bulletin_id,),
            )
            conn.execute(
                "DELETE FROM bulletin_sync_queue WHERE bulletin_id = ?;",
                (bulletin_id,),
            )
            return cursor.rowcount > 0

    def clear_archived_bulletins(self) -> int:
        """Permanently removes all dismissed/archived bulletins.

        Returns:
            int: Number of deleted rows.
        """
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                "DELETE FROM system_bulletins WHERE is_dismissed = 1;",
            )
            return cursor.rowcount
