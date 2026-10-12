"""Repository for persistent stream link status tracking."""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from backend.config.settings import settings
from backend.core.db import db_manager


class LinkStatusEntry(BaseModel):
    """Cached status model for a single stream URL."""

    status: str = Field(default="unchecked", description="Link status: online, offline, redirect, unchecked")
    code: int = Field(default=0, description="HTTP response status code")
    cors_supported: bool = Field(default=False, description="Server returned Access-Control-Allow-Origin header")
    needs_proxy: bool = Field(default=False, description="Stream is online but lacks CORS headers requiring proxy")
    error_message: Optional[str] = Field(default=None, description="Optional playback error details")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Last check timestamp string",
    )


class LinkStatusRepository:
    """Thread-safe persistent repository for link test results using direct SQLite WAL queries."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        """Initializes repository with optional file path override.

        Args:
            file_path (Optional[Path]): Override path to database file.
        """
        self._file_path = file_path
        self._lock = threading.RLock()

    @property
    def file_path(self) -> Path:
        """Dynamically resolves target database file path.

        Returns:
            Path: Resolved database file path.
        """
        if self._file_path is not None:
            return self._file_path
        return settings.data_dir / "pluvira_epg.db"

    @file_path.setter
    def file_path(self, value: Optional[Path]) -> None:
        """Sets explicit database file path override."""
        self._file_path = value

    @property
    def db_path(self) -> Path:
        """Resolves physical SQLite database path."""
        return self.file_path

    def _get_conn(self) -> sqlite3.Connection:
        """Opens SQLite connection and ensures link_status table exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        conn = db_manager.get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS link_status (
                    url TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    code INTEGER NOT NULL,
                    cors_supported INTEGER NOT NULL,
                    needs_proxy INTEGER NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL
                );
                """
            )
        return conn

    def get_status(self, url: str) -> LinkStatusEntry:
        """Retrieves link status entry for a given URL identity key directly from SQLite.

        Args:
            url (str): Channel original URL key.

        Returns:
            LinkStatusEntry: Status entry from SQLite database or unchecked default.
        """
        with self._lock:
            try:
                with self._get_conn() as conn:
                    cursor = conn.execute(
                        "SELECT status, code, cors_supported, needs_proxy, error_message, timestamp FROM link_status WHERE url = ?",
                        (url,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return LinkStatusEntry(
                            status=row[0],
                            code=row[1],
                            cors_supported=bool(row[2]),
                            needs_proxy=bool(row[3]),
                            error_message=row[4],
                            timestamp=row[5],
                        )
            except Exception as e:
                logging.error(f"Failed to query link_status from SQLite '{self.db_path}': {e}")
            return LinkStatusEntry(status="unchecked", code=0)

    def update_status(
        self,
        url: str,
        status: str,
        code: int,
        cors_supported: bool = False,
        needs_proxy: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Persists link status entry directly into SQLite WAL database.

        Args:
            url (str): Channel original URL key.
            status (str): Status string ('online', 'offline', 'redirect').
            code (int): HTTP status code.
            cors_supported (bool): Whether server returned valid CORS headers.
            needs_proxy (bool): Whether stream requires backend proxying for WebUI playback.
            error_message (Optional[str]): Optional client playback error description.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            try:
                with self._get_conn() as conn:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO link_status (url, status, code, cors_supported, needs_proxy, error_message, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(url) DO UPDATE SET
                                status = excluded.status,
                                code = excluded.code,
                                cors_supported = excluded.cors_supported,
                                needs_proxy = excluded.needs_proxy,
                                error_message = excluded.error_message,
                                timestamp = excluded.timestamp
                            """,
                            (
                                url,
                                status,
                                code,
                                1 if cors_supported else 0,
                                1 if needs_proxy else 0,
                                error_message,
                                now_str,
                            ),
                        )
            except Exception as e:
                logging.error(f"Failed to update link_status in SQLite '{self.db_path}': {e}")

    def reset_all(self) -> None:
        """Truncates all link status records directly in SQLite database."""
        with self._lock:
            try:
                with self._get_conn() as conn:
                    with conn:
                        conn.execute("DELETE FROM link_status")
            except Exception as e:
                logging.error(f"Failed to reset link_status in SQLite '{self.db_path}': {e}")


link_status_repo = LinkStatusRepository()
