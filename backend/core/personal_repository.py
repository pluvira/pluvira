"""Repository for personal playlists, channels, slots, and suggestions."""

import sqlite3
from pathlib import Path
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from backend.config.settings import settings
from backend.core.db import db_manager
from backend.core.health_ranking import HealthRankingEngine
from backend.config.models import ChannelSlot


class PersonalPlaylistRepository:
    """Encapsulates SQLite operations for personal curated playlists."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initializes repository and ensures schema exists.

        Args:
            data_dir (Optional[Path]): Persistent data directory.
        """
        self.data_dir = data_dir or settings.data_dir
        self.init_personal_playlist_tables()

    def get_conn(self) -> sqlite3.Connection:
        """Returns SQLite connection to pluvira_main.db."""
        return db_manager.get_connection(db_manager.get_db_path())

    def init_personal_playlist_tables(self) -> None:
        """Initializes SQLite tables for personal playlists, channels, slots, and suggestions."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        conn = self.get_conn()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS personal_playlists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    export_token TEXT NOT NULL DEFAULT '',
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS personal_channels (
                    id TEXT PRIMARY KEY,
                    playlist_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    logo TEXT DEFAULT '',
                    epg_id TEXT DEFAULT '',
                    group_name TEXT DEFAULT '',
                    custom_order INTEGER NOT NULL DEFAULT 0,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_slots (
                    id TEXT PRIMARY KEY,
                    personal_channel_id TEXT NOT NULL,
                    slot_index INTEGER NOT NULL DEFAULT 0,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    user_agent TEXT,
                    health_score REAL NOT NULL DEFAULT 100.0,
                    is_locked INTEGER NOT NULL DEFAULT 0,
                    consecutive_errors INTEGER NOT NULL DEFAULT 0,
                    quarantined_at TEXT,
                    FOREIGN KEY(personal_channel_id) REFERENCES personal_channels(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_suggestions (
                    id TEXT PRIMARY KEY,
                    personal_channel_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    user_agent TEXT,
                    confidence_score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(personal_channel_id) REFERENCES personal_channels(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pers_ch_playlist ON personal_channels(playlist_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_slots_channel ON channel_slots(personal_channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_sug_channel ON channel_suggestions(personal_channel_id);")

    def ensure_default_playlist(self) -> None:
        """Ensures the default system playlist exists."""
        now_str = datetime.now(timezone.utc).isoformat()
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO personal_playlists (id, name, export_token, is_default, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("default", "My List", "", 1, now_str),
                )

    def get_playlists(self) -> List[Dict[str, Any]]:
        """Retrieves all configured personal playlists."""
        self.ensure_default_playlist()
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, name, export_token, is_default, created_at FROM personal_playlists ORDER BY is_default DESC, name ASC"
            )
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "export_token": r[2],
                    "is_default": bool(r[3]),
                    "created_at": r[4],
                }
                for r in cursor.fetchall()
            ]

    def get_playlist_by_id(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single personal playlist by ID."""
        self.ensure_default_playlist()
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, name, export_token, is_default, created_at FROM personal_playlists WHERE id = ?",
                (playlist_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r[0],
                "name": r[1],
                "export_token": r[2],
                "is_default": bool(r[3]),
                "created_at": r[4],
            }

    def create_playlist(
        self, playlist_id: str, name: str, export_token: str, is_default: bool, created_at: str
    ) -> None:
        """Creates a personal playlist record."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO personal_playlists (id, name, export_token, is_default, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (playlist_id, name, export_token, 1 if is_default else 0, created_at),
                )

    def update_playlist(self, playlist_id: str, name: str, export_token: str) -> None:
        """Updates a personal playlist record."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE personal_playlists SET name = ?, export_token = ? WHERE id = ?",
                    (name, export_token, playlist_id),
                )

    def update_export_token(self, playlist_id: str, export_token: str) -> None:
        """Updates the export token of a personal playlist."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    "UPDATE personal_playlists SET export_token = ? WHERE id = ?",
                    (export_token, playlist_id),
                )

    def delete_playlist(self, playlist_id: str) -> None:
        """Deletes a custom personal playlist and its associated channels, slots, and suggestions."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM channel_slots WHERE personal_channel_id IN (SELECT id FROM personal_channels WHERE playlist_id = ?)",
                    (playlist_id,),
                )
                conn.execute(
                    "DELETE FROM channel_suggestions WHERE personal_channel_id IN (SELECT id FROM personal_channels WHERE playlist_id = ?)",
                    (playlist_id,),
                )
                conn.execute("DELETE FROM personal_channels WHERE playlist_id = ?", (playlist_id,))
                conn.execute("DELETE FROM personal_playlists WHERE id = ?", (playlist_id,))

    def get_channels(self, playlist_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieves all personal channels for a given playlist with slots and suggestions."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT id, playlist_id, name, logo, epg_id, group_name, custom_order, is_pinned, created_at
                FROM personal_channels
                WHERE playlist_id = ?
                ORDER BY is_pinned DESC, custom_order ASC, name ASC
                """,
                (playlist_id,),
            )
            ch_rows = cursor.fetchall()
            if not ch_rows:
                return []

            ch_ids = [r[0] for r in ch_rows]
            placeholders = ",".join("?" * len(ch_ids))

            slots_cursor = conn.execute(
                f"""
                SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at
                FROM channel_slots
                WHERE personal_channel_id IN ({placeholders})
                ORDER BY slot_index ASC
                """,
                ch_ids,
            )
            slots_map: Dict[str, List[Dict[str, Any]]] = {}
            for s in slots_cursor.fetchall():
                ch_id = s[1]
                if ch_id not in slots_map:
                    slots_map[ch_id] = []
                slots_map[ch_id].append({
                    "id": s[0],
                    "personal_channel_id": s[1],
                    "slot_index": s[2],
                    "url": s[3],
                    "source": s[4],
                    "user_agent": s[5],
                    "health_score": s[6],
                    "is_locked": bool(s[7]),
                    "consecutive_errors": s[8],
                    "quarantined_at": s[9],
                })

            sug_cursor = conn.execute(
                f"""
                SELECT id, personal_channel_id, url, source, user_agent, confidence_score, created_at
                FROM channel_suggestions
                WHERE personal_channel_id IN ({placeholders})
                ORDER BY confidence_score DESC
                """,
                ch_ids,
            )
            sug_map: Dict[str, List[Dict[str, Any]]] = {}
            for sg in sug_cursor.fetchall():
                ch_id = sg[1]
                if ch_id not in sug_map:
                    sug_map[ch_id] = []
                sug_map[ch_id].append({
                    "id": sg[0],
                    "personal_channel_id": sg[1],
                    "url": sg[2],
                    "source": sg[3],
                    "user_agent": sg[4],
                    "confidence_score": sg[5],
                    "created_at": sg[6],
                })

            result = []
            for r in ch_rows:
                cid = r[0]
                result.append({
                    "id": cid,
                    "playlist_id": r[1],
                    "name": r[2],
                    "logo": r[3] or "",
                    "epg_id": r[4] or "",
                    "group": r[5] or "",
                    "custom_order": r[6],
                    "is_pinned": bool(r[7]),
                    "created_at": r[8],
                    "slots": slots_map.get(cid, []),
                    "suggestions": sug_map.get(cid, []),
                })
            return result

    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single personal channel by ID with its slots and suggestions."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT id, playlist_id, name, logo, epg_id, group_name, custom_order, is_pinned, created_at
                FROM personal_channels
                WHERE id = ?
                """,
                (channel_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None

            cid = r[0]
            slots_cursor = conn.execute(
                """
                SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at
                FROM channel_slots
                WHERE personal_channel_id = ?
                ORDER BY slot_index ASC
                """,
                (cid,),
            )
            slots = [
                {
                    "id": s[0],
                    "personal_channel_id": s[1],
                    "slot_index": s[2],
                    "url": s[3],
                    "source": s[4],
                    "user_agent": s[5],
                    "health_score": s[6],
                    "is_locked": bool(s[7]),
                    "consecutive_errors": s[8],
                    "quarantined_at": s[9],
                }
                for s in slots_cursor.fetchall()
            ]

            sug_cursor = conn.execute(
                """
                SELECT id, personal_channel_id, url, source, user_agent, confidence_score, created_at
                FROM channel_suggestions
                WHERE personal_channel_id = ?
                ORDER BY confidence_score DESC
                """,
                (cid,),
            )
            suggestions = [
                {
                    "id": sg[0],
                    "personal_channel_id": sg[1],
                    "url": sg[2],
                    "source": sg[3],
                    "user_agent": sg[4],
                    "confidence_score": sg[5],
                    "created_at": sg[6],
                }
                for sg in sug_cursor.fetchall()
            ]

            return {
                "id": cid,
                "playlist_id": r[1],
                "name": r[2],
                "logo": r[3] or "",
                "epg_id": r[4] or "",
                "group": r[5] or "",
                "custom_order": r[6],
                "is_pinned": bool(r[7]),
                "created_at": r[8],
                "slots": slots,
                "suggestions": suggestions,
            }

    def insert_channel(self, payload: Any, created_at: str) -> None:
        """Inserts a new personal channel and saves its slots."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO personal_channels (id, playlist_id, name, logo, epg_id, group_name, custom_order, is_pinned, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.id,
                        payload.playlist_id,
                        payload.name,
                        payload.logo or "",
                        payload.epg_id or "",
                        payload.group or "",
                        payload.custom_order,
                        1 if payload.is_pinned else 0,
                        created_at,
                    ),
                )
                if payload.slots:
                    for s in payload.slots:
                        if not s.id:
                            s.id = f"slot_{uuid.uuid4().hex[:12]}"
                    self.reorder_and_save_slots(conn, payload.id, payload.slots)

    def update_channel_metadata(
        self,
        channel_id: str,
        name: str,
        logo: str,
        epg_id: str,
        group_name: str,
        custom_order: int,
        is_pinned: bool,
    ) -> None:
        """Updates personal channel attributes."""
        with self.get_conn() as conn:
            with conn:
                conn.execute(
                    """
                    UPDATE personal_channels
                    SET name = ?, logo = ?, epg_id = ?, group_name = ?, custom_order = ?, is_pinned = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        logo,
                        epg_id,
                        group_name,
                        int(custom_order),
                        1 if is_pinned else 0,
                        channel_id,
                    ),
                )

    def delete_channel(self, channel_id: str) -> None:
        """Deletes a personal channel and its associated slots and suggestions."""
        with self.get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM channel_slots WHERE personal_channel_id = ?", (channel_id,))
                conn.execute(
                    "DELETE FROM channel_suggestions WHERE personal_channel_id = ?", (channel_id,)
                )
                conn.execute("DELETE FROM personal_channels WHERE id = ?", (channel_id,))

    def update_channel_slots(self, personal_channel_id: str, slots: List[ChannelSlot]) -> None:
        """Reorders and saves slots for a personal channel."""
        with self.get_conn() as conn:
            with conn:
                self.reorder_and_save_slots(conn, personal_channel_id, slots)

    def update_slot_order(self, personal_channel_id: str, slot_ids: List[str]) -> None:
        """Updates slot_index order manually for stream slots."""
        with self.get_conn() as conn:
            with conn:
                for idx, sid in enumerate(slot_ids[:7]):
                    conn.execute(
                        "UPDATE channel_slots SET slot_index = ? WHERE id = ? AND personal_channel_id = ?",
                        (idx, sid, personal_channel_id),
                    )

    def sync_pro_evaluated_slots(self, updated_channels: List[Dict[str, Any]]) -> None:
        """Updates slot states from Pro failover evaluation results."""
        with self.get_conn() as conn:
            with conn:
                for pch in updated_channels:
                    if "slots" in pch:
                        for slot in pch.get("slots", []):
                            conn.execute(
                                """
                                UPDATE channel_slots
                                SET slot_index = ?, health_score = ?, consecutive_errors = ?, quarantined_at = ?
                                WHERE id = ? AND personal_channel_id = ?
                                """,
                                (
                                    slot.get("slot_index", 0),
                                    float(slot.get("health_score", 100.0)),
                                    int(slot.get("consecutive_errors", 0)),
                                    slot.get("quarantined_at"),
                                    slot.get("id"),
                                    pch.get("id"),
                                ),
                            )

    def get_suggestion_by_id(self, suggestion_id: str) -> Optional[Tuple[Any, ...]]:
        """Retrieves a single suggestion by ID."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT id, personal_channel_id, url, source, user_agent, confidence_score
                FROM channel_suggestions
                WHERE id = ?
                """,
                (suggestion_id,),
            )
            return cursor.fetchone()

    def delete_suggestion(self, suggestion_id: str) -> None:
        """Deletes a suggestion by ID."""
        with self.get_conn() as conn:
            with conn:
                conn.execute("DELETE FROM channel_suggestions WHERE id = ?", (suggestion_id,))

    def purge_quarantined_slots(self, playlist_id: Optional[str] = None) -> int:
        """Deletes quarantined stream slots and reorders remaining slots."""
        with self.get_conn() as conn:
            with conn:
                if playlist_id:
                    cursor = conn.execute(
                        """
                        SELECT DISTINCT personal_channel_id FROM channel_slots
                        WHERE quarantined_at IS NOT NULL
                          AND personal_channel_id IN (SELECT id FROM personal_channels WHERE playlist_id = ?)
                        """,
                        (playlist_id,),
                    )
                    affected_channels = [r[0] for r in cursor.fetchall()]
                    del_cursor = conn.execute(
                        """
                        DELETE FROM channel_slots
                        WHERE quarantined_at IS NOT NULL
                          AND personal_channel_id IN (SELECT id FROM personal_channels WHERE playlist_id = ?)
                        """,
                        (playlist_id,),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT DISTINCT personal_channel_id FROM channel_slots WHERE quarantined_at IS NOT NULL"
                    )
                    affected_channels = [r[0] for r in cursor.fetchall()]
                    del_cursor = conn.execute(
                        "DELETE FROM channel_slots WHERE quarantined_at IS NOT NULL"
                    )

                purged_count = del_cursor.rowcount

                for pch_id in affected_channels:
                    s_cursor = conn.execute(
                        """
                        SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at
                        FROM channel_slots
                        WHERE personal_channel_id = ?
                        ORDER BY slot_index ASC
                        """,
                        (pch_id,),
                    )
                    slot_objs = [
                        ChannelSlot(
                            id=row[0],
                            personal_channel_id=row[1],
                            slot_index=row[2],
                            url=row[3],
                            source=row[4],
                            user_agent=row[5],
                            health_score=row[6],
                            is_locked=bool(row[7]),
                            consecutive_errors=row[8],
                            quarantined_at=row[9],
                        )
                        for row in s_cursor.fetchall()
                    ]
                    self.reorder_and_save_slots(conn, pch_id, slot_objs)
                return purged_count

    def purge_expired_quarantined_slots(self, cutoff_iso: str) -> int:
        """Deletes quarantined stream slots older than cutoff date."""
        with self.get_conn() as conn:
            with conn:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT personal_channel_id FROM channel_slots
                    WHERE quarantined_at IS NOT NULL AND quarantined_at <= ?
                    """,
                    (cutoff_iso,),
                )
                affected_channels = [r[0] for r in cursor.fetchall()]

                del_cursor = conn.execute(
                    """
                    DELETE FROM channel_slots
                    WHERE quarantined_at IS NOT NULL AND quarantined_at <= ?
                    """,
                    (cutoff_iso,),
                )
                purged_count = del_cursor.rowcount

                for pch_id in affected_channels:
                    s_cursor = conn.execute(
                        """
                        SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at
                        FROM channel_slots
                        WHERE personal_channel_id = ?
                        ORDER BY slot_index ASC
                        """,
                        (pch_id,),
                    )
                    slot_objs = [
                        ChannelSlot(
                            id=row[0],
                            personal_channel_id=row[1],
                            slot_index=row[2],
                            url=row[3],
                            source=row[4],
                            user_agent=row[5],
                            health_score=row[6],
                            is_locked=bool(row[7]),
                            consecutive_errors=row[8],
                            quarantined_at=row[9],
                        )
                        for row in s_cursor.fetchall()
                    ]
                    self.reorder_and_save_slots(conn, pch_id, slot_objs)
                return purged_count

    def reorder_and_save_slots(self, conn: sqlite3.Connection, personal_channel_id: str, slots: List[ChannelSlot]) -> None:
        """Reorders slots by health score and saves them to the database.

        Args:
            conn (sqlite3.Connection): Active SQLite connection.
            personal_channel_id (str): Target personal channel ID.
            slots (List[ChannelSlot]): List of slots to reorder and save.
        """
        reordered = HealthRankingEngine.reorder_slots(slots)
        conn.execute(
            "DELETE FROM channel_slots WHERE personal_channel_id = ?", (personal_channel_id,)
        )
        for s in reordered:
            conn.execute(
                """
                INSERT INTO channel_slots (id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s.id,
                    personal_channel_id,
                    s.slot_index,
                    s.url,
                    s.source,
                    s.user_agent,
                    s.health_score,
                    1 if s.is_locked else 0,
                    s.consecutive_errors,
                    s.quarantined_at,
                ),
            )

    def sync_slot_health(
        self,
        url: str,
        original_url: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Synchronizes stream health score, consecutive errors, and slot reordering across personal channels."""
        search_urls = [u for u in [url, original_url] if u]
        if not search_urls:
            return

        try:
            conn = self.get_conn()
            with conn:
                placeholders = ",".join("?" * len(search_urls))
                cursor = conn.execute(
                    f"SELECT id, personal_channel_id, health_score, consecutive_errors, is_locked, quarantined_at FROM channel_slots WHERE url IN ({placeholders})",
                    search_urls,
                )
                matching_slots = cursor.fetchall()
                if not matching_slots:
                    return

                affected_channel_ids = set()
                now_str = datetime.now(timezone.utc).isoformat()
                is_offline = str(status).lower() in ("offline", "ko", "error")

                for s_id, pch_id, h_score, c_errs, is_locked, q_at in matching_slots:
                    affected_channel_ids.add(pch_id)
                    if is_offline:
                        new_errs = int(c_errs or 0) + 1
                        new_score = max(0.0, float(h_score or 100.0) - 30.0)
                        is_quarantine = HealthRankingEngine.eval_quarantine_status(new_score, new_errs)
                        new_q = q_at or (now_str if is_quarantine else None)
                    else:
                        new_errs = 0
                        new_score = HealthRankingEngine.calculate_health_score("online", uptime_pct=100.0)
                        new_q = None

                    conn.execute(
                        """
                        UPDATE channel_slots
                        SET health_score = ?, consecutive_errors = ?, quarantined_at = ?
                        WHERE id = ?
                        """,
                        (new_score, new_errs, new_q, s_id),
                    )

                for pch_id in affected_channel_ids:
                    s_cursor = conn.execute(
                        """
                        SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at
                        FROM channel_slots
                        WHERE personal_channel_id = ?
                        """,
                        (pch_id,),
                    )
                    slot_objs = [
                        ChannelSlot(
                            id=row[0],
                            personal_channel_id=row[1],
                            slot_index=row[2],
                            url=row[3],
                            source=row[4],
                            user_agent=row[5],
                            health_score=row[6],
                            is_locked=bool(row[7]),
                            consecutive_errors=row[8],
                            quarantined_at=row[9],
                        )
                        for row in s_cursor.fetchall()
                    ]
                    self.reorder_and_save_slots(conn, pch_id, slot_objs)
        except Exception as e:
            logging.debug(f"Slot health sync skipped for '{url}': {e}")

    def get_all_playlists_flat(self) -> List[dict]:
        """Retrieves all personal curated playlists as a list of dicts for backup export."""
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, export_token, is_default, created_at FROM personal_playlists ORDER BY id")
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "export_token": r[2] or "",
                    "is_default": bool(r[3]),
                    "created_at": r[4] or "",
                }
                for r in cur.fetchall()
            ]

    def get_all_channels_with_slots_flat(self) -> List[dict]:
        """Retrieves all personal channels with slots and suggestions as dicts for backup export."""
        with self.get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, playlist_id, name, logo, epg_id, group_name, custom_order, is_pinned, created_at "
                "FROM personal_channels ORDER BY playlist_id, custom_order"
            )
            ch_rows = cur.fetchall()
            channels = []
            now_iso = datetime.now(timezone.utc).isoformat()
            for ch in ch_rows:
                ch_id = ch[0]
                cur.execute(
                    "SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, "
                    "is_locked, consecutive_errors, quarantined_at FROM channel_slots WHERE personal_channel_id = ? "
                    "ORDER BY slot_index",
                    (ch_id,),
                )
                slots = [
                    {
                        "id": s[0],
                        "personal_channel_id": s[1],
                        "slot_index": s[2],
                        "url": s[3],
                        "source": s[4],
                        "user_agent": s[5] or "",
                        "health_score": float(s[6]),
                        "is_locked": bool(s[7]),
                        "consecutive_errors": int(s[8]),
                        "quarantined_at": s[9],
                    }
                    for s in cur.fetchall()
                ]

                cur.execute(
                    "SELECT id, personal_channel_id, url, source, user_agent, confidence_score, created_at "
                    "FROM channel_suggestions WHERE personal_channel_id = ? ORDER BY confidence_score DESC",
                    (ch_id,),
                )
                suggestions = [
                    {
                        "id": sg[0],
                        "personal_channel_id": sg[1],
                        "url": sg[2],
                        "source": sg[3],
                        "user_agent": sg[4] or "",
                        "confidence_score": float(sg[5]),
                        "created_at": sg[6],
                    }
                    for sg in cur.fetchall()
                ]

                channels.append(
                    {
                        "id": ch[0],
                        "playlist_id": ch[1],
                        "name": ch[2],
                        "logo": ch[3] or "",
                        "epg_id": ch[4] or "",
                        "group": ch[5] or "",
                        "custom_order": ch[6],
                        "is_pinned": bool(ch[7]),
                        "created_at": ch[8] or now_iso,
                        "slots": slots,
                        "suggestions": suggestions,
                    }
                )
            return channels

    def persist_playlists_and_channels(
        self,
        incoming_playlists: List[dict],
        incoming_pchannels: List[dict],
        destructive: bool = False,
    ) -> None:
        """Persists personal playlists and channels into SQLite tables."""
        with self.get_conn() as conn:
            cur = conn.cursor()
            if destructive:
                cur.execute("DELETE FROM channel_suggestions")
                cur.execute("DELETE FROM channel_slots")
                cur.execute("DELETE FROM personal_channels")
                cur.execute("DELETE FROM personal_playlists")

            now_iso = datetime.now(timezone.utc).isoformat()
            if not any(p.get("id") == "default" for p in incoming_playlists):
                cur.execute(
                    "INSERT OR IGNORE INTO personal_playlists (id, name, export_token, is_default, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("default", "My List", "", 1, now_iso),
                )

            for p in incoming_playlists:
                cur.execute(
                    "INSERT OR REPLACE INTO personal_playlists (id, name, export_token, is_default, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        p.get("id"),
                        p.get("name"),
                        p.get("export_token", ""),
                        1 if p.get("is_default") else 0,
                        p.get("created_at") or now_iso,
                    ),
                )

            for pch in incoming_pchannels:
                cur.execute(
                    "INSERT OR REPLACE INTO personal_channels "
                    "(id, playlist_id, name, logo, epg_id, group_name, custom_order, is_pinned, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        pch.get("id"),
                        pch.get("playlist_id", "default"),
                        pch.get("name"),
                        pch.get("logo", ""),
                        pch.get("epg_id", ""),
                        pch.get("group", "") or pch.get("group_title", ""),
                        pch.get("custom_order", 0),
                        1 if pch.get("is_pinned") else 0,
                        pch.get("created_at") or now_iso,
                    ),
                )
                for slot in pch.get("slots", []):
                    cur.execute(
                        "INSERT OR REPLACE INTO channel_slots "
                        "(id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            slot.get("id"),
                            pch.get("id"),
                            slot.get("slot_index", 0),
                            slot.get("url"),
                            slot.get("source"),
                            slot.get("user_agent", ""),
                            slot.get("health_score", 100.0),
                            1 if slot.get("is_locked") else 0,
                            slot.get("consecutive_errors", 0),
                            slot.get("quarantined_at"),
                        ),
                    )
                for sug in pch.get("suggestions", []):
                    cur.execute(
                        "INSERT OR REPLACE INTO channel_suggestions "
                        "(id, personal_channel_id, url, source, user_agent, confidence_score, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            sug.get("id"),
                            pch.get("id"),
                            sug.get("url"),
                            sug.get("source"),
                            sug.get("user_agent", ""),
                            sug.get("confidence_score", 0.0),
                            sug.get("created_at") or now_iso,
                        ),
                    )
            conn.commit()
