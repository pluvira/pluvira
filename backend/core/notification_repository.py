"""Repository for managing notification settings and webhook targets in SQLite pluvira_main.db."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend.config.models import NotificationSettings, NotificationEventConfig
from backend.core.db import DatabaseManager
from backend.core.base_repository import BaseRepository


class NotificationRepository(BaseRepository):
    """Encapsulates SQLite operations for system notification settings and target webhook URLs."""

    table_name = "notification_settings"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes notification tables."""
        DatabaseManager.init_notification_tables(conn)

    def get_settings(self) -> NotificationSettings:
        """Retrieves current notification settings and target webhook URLs from SQLite.

        Returns:
            NotificationSettings: Populated notification settings model.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT enabled, events_json FROM notification_settings WHERE id = 1;")
            row = cursor.fetchone()

            cursor.execute("SELECT url FROM notification_targets ORDER BY id ASC;")
            url_rows = cursor.fetchall()
            urls = [r[0] for r in url_rows]

            if not row:
                return NotificationSettings(enabled=False, urls=urls, events=NotificationEventConfig())

            enabled = bool(row[0])
            events_json = row[1] or "{}"
            try:
                events_dict = json.loads(events_json)
                events_cfg = NotificationEventConfig.model_validate(events_dict)
            except Exception as e:
                logging.warning(f"Failed to parse notification events JSON: {e}. Using defaults.")
                events_cfg = NotificationEventConfig()

            return NotificationSettings(enabled=enabled, urls=urls, events=events_cfg)
        finally:
            conn.close()

    def save_settings(self, settings: NotificationSettings) -> None:
        """Atomically persists notification settings and target webhook URLs.

        Args:
            settings (NotificationSettings): Settings model to persist.
        """
        conn = self.get_conn()
        try:
            events_json = settings.events.model_dump_json() if settings.events else "{}"
            enabled_val = 1 if settings.enabled else 0

            with conn:
                conn.execute(
                    """
                    INSERT INTO notification_settings (id, enabled, events_json, updated_at)
                    VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        enabled = excluded.enabled,
                        events_json = excluded.events_json,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (enabled_val, events_json),
                )

                conn.execute("DELETE FROM notification_targets;")
                if settings.urls:
                    for u in settings.urls:
                        clean_url = u.strip() if u else ""
                        if clean_url:
                            conn.execute(
                                "INSERT OR IGNORE INTO notification_targets (url) VALUES (?);",
                                (clean_url,),
                            )
        finally:
            conn.close()

    def get_urls(self) -> List[str]:
        """Retrieves list of configured target notification webhook URLs.

        Returns:
            List[str]: Target URLs list.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM notification_targets ORDER BY id ASC;")
            return [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

    def set_urls(self, urls: List[str]) -> None:
        """Atomically replaces all target notification webhook URLs.

        Args:
            urls (List[str]): New target URLs list.
        """
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM notification_targets;")
                for u in urls:
                    clean_url = u.strip() if u else ""
                    if clean_url:
                        conn.execute(
                            "INSERT OR IGNORE INTO notification_targets (url) VALUES (?);",
                            (clean_url,),
                        )
        finally:
            conn.close()

    def add_url(self, url: str) -> bool:
        """Adds a target notification webhook URL if not already present.

        Args:
            url (str): Target webhook URL.

        Returns:
            bool: True if inserted, False if duplicate or empty.
        """
        clean_url = url.strip() if url else ""
        if not clean_url:
            return False

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO notification_targets (url) VALUES (?);",
                    (clean_url,),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def remove_url(self, url: str) -> bool:
        """Removes a target notification webhook URL.

        Args:
            url (str): Target webhook URL to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        clean_url = url.strip() if url else ""
        if not clean_url:
            return False

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM notification_targets WHERE url = ?;", (clean_url,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def set_enabled(self, enabled: bool) -> None:
        """Toggles the global notifications enabled flag in SQLite.

        Args:
            enabled (bool): New enabled status boolean.
        """
        conn = self.get_conn()
        try:
            enabled_val = 1 if enabled else 0
            with conn:
                conn.execute(
                    """
                    INSERT INTO notification_settings (id, enabled, events_json, updated_at)
                    VALUES (1, ?, '{}', CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        enabled = excluded.enabled,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (enabled_val,),
                )
        finally:
            conn.close()

    def update_events_config(self, events: NotificationEventConfig) -> None:
        """Updates the notification event triggers and thresholds matrix.

        Args:
            events (NotificationEventConfig): Event triggers configuration model.
        """
        conn = self.get_conn()
        try:
            events_json = events.model_dump_json()
            with conn:
                conn.execute(
                    """
                    INSERT INTO notification_settings (id, enabled, events_json, updated_at)
                    VALUES (1, 0, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        events_json = excluded.events_json,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (events_json,),
                )
        finally:
            conn.close()

    def apply_preset(self, preset_name: str) -> bool:
        """Applies a preset configuration profile to notification event triggers.

        Args:
            preset_name (str): Preset profile name.

        Returns:
            bool: True if applied successfully, False if invalid preset name.
        """
        from backend.services.notification_service import NotificationService

        settings = self.get_settings()
        applied = NotificationService.apply_preset_to_settings(settings, preset_name)
        if applied:
            self.save_settings(settings)
        return applied

    def clear_all(self) -> None:
        """Truncates notification targets and resets settings to default disabled state."""
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM notification_targets;")
                conn.execute("DELETE FROM notification_settings;")
        finally:
            conn.close()
