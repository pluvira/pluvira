"""Execution history models and SQLite repository implementation."""

import json
import uuid
import threading
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime

import sqlite3

from backend.config.settings import settings
from backend.core.db import db_manager


class SourceStats(BaseModel):
    """Per-source channel statistics model."""

    source_name: str = Field(..., description="Name of IPTV source")
    channels: int = Field(default=0, description="Total extracted channels count")
    matched_epg: int = Field(default=0, description="Matched EPG channels count")


class EpgSourceStats(BaseModel):
    """Per-EPG-source programme statistics model."""

    source_name: str = Field(..., description="Name of EPG source")
    channels: int = Field(default=0, description="Total mapped EPG channels count")
    programmes: int = Field(default=0, description="Total parsed EPG programmes count")
    duration_s: float = Field(default=0.0, description="Acquisition and parsing duration in seconds")
    engine: str = Field(default="core", description="Ingestion engine used ('pro' or 'core')")


class HistoryRecord(BaseModel):
    """Execution history record model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique record identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Execution timestamp string",
    )
    mode: str = Field(default="full", description="Execution mode: full, raw, m3u, or epg")
    duration: float = Field(..., description="Execution duration in seconds")
    status: str = Field(..., description="Execution status: success or failed")
    total_channels: int = Field(default=0)
    matched_channels: int = Field(default=0)
    missing_channels: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    sources_stats: List[SourceStats] = Field(default_factory=list)
    is_turbo: bool = Field(default=False, description="Whether Pro Turbo engine was used")
    epg_stats: List[EpgSourceStats] = Field(default_factory=list)
    trigger: str = Field(default="manual", description="Trigger source: 'manual' or 'scheduled'")
    channels_modified: int = Field(default=0, description="Total channels modified by rewrites")
    turbo_rewrites_duration_s: float = Field(default=0.0, description="Turbo rewrites execution duration")
    is_turbo_rewrites: bool = Field(default=False, description="Whether Turbo Rewrites engine was used")


class SQLiteHistoryRepository:
    """Thread-safe execution history repository using SQLite storage with max 100 entries limit."""

    def __init__(self, file_path: Optional[Path] = None, temp_dir: Optional[Path] = None) -> None:
        """Initializes repository with optional file and temp directory overrides.

        Args:
            file_path (Optional[Path]): Override path to database file.
            temp_dir (Optional[Path]): Override RAM disk temp directory.
        """
        self._file_path = file_path
        self._temp_dir = temp_dir
        self._lock = threading.RLock()

    @property
    def file_path(self) -> Path:
        """Dynamically resolves target database file path."""
        if self._file_path is not None:
            return self._file_path
        return db_manager.get_db_path()

    @file_path.setter
    def file_path(self, value: Optional[Path]) -> None:
        """Sets explicit database file path override."""
        self._file_path = value

    @property
    def db_path(self) -> Path:
        """Resolves physical SQLite database path."""
        return self.file_path

    @property
    def temp_dir(self) -> Path:
        """Dynamically resolves RAM disk temp directory path."""
        if self._temp_dir is not None:
            return self._temp_dir
        return settings.temp_dir

    @temp_dir.setter
    def temp_dir(self, value: Optional[Path]) -> None:
        """Sets explicit temp directory path override."""
        self._temp_dir = value

    def _get_conn(self) -> sqlite3.Connection:
        """Opens SQLite connection and ensures execution_history table exists."""
        conn = db_manager.get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_history (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    duration REAL NOT NULL,
                    status TEXT NOT NULL,
                    total_channels INTEGER NOT NULL,
                    matched_channels INTEGER NOT NULL,
                    missing_channels INTEGER NOT NULL,
                    error_message TEXT,
                    sources_stats_json TEXT NOT NULL,
                    is_turbo INTEGER NOT NULL DEFAULT 0,
                    epg_stats_json TEXT NOT NULL DEFAULT '[]',
                    trigger TEXT NOT NULL DEFAULT 'manual'
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(execution_history)")
            cols = {row[1] for row in cursor.fetchall()}
            if "is_turbo" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN is_turbo INTEGER NOT NULL DEFAULT 0")
            if "epg_stats_json" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN epg_stats_json TEXT NOT NULL DEFAULT '[]'")
            if "trigger" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN trigger TEXT NOT NULL DEFAULT 'manual'")
            if "channels_modified" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN channels_modified INTEGER NOT NULL DEFAULT 0")
            if "turbo_rewrites_duration_s" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN turbo_rewrites_duration_s REAL NOT NULL DEFAULT 0.0")
            if "is_turbo_rewrites" not in cols:
                conn.execute("ALTER TABLE execution_history ADD COLUMN is_turbo_rewrites INTEGER NOT NULL DEFAULT 0")
        return conn



    def add(self, record: HistoryRecord) -> None:
        """Adds a new history record and enforces max 100 entries limit."""
        with self._lock:
            try:
                stats_json = json.dumps([s.model_dump() for s in record.sources_stats])
                epg_stats_json = json.dumps([s.model_dump() for s in record.epg_stats])
                with self._get_conn() as conn:
                    with conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO execution_history
                            (id, timestamp, mode, duration, status, total_channels, matched_channels, missing_channels, error_message, sources_stats_json, is_turbo, epg_stats_json, trigger, channels_modified, turbo_rewrites_duration_s, is_turbo_rewrites)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                record.id,
                                record.timestamp,
                                record.mode,
                                record.duration,
                                record.status,
                                record.total_channels,
                                record.matched_channels,
                                record.missing_channels,
                                record.error_message,
                                stats_json,
                                1 if record.is_turbo else 0,
                                epg_stats_json,
                                record.trigger,
                                record.channels_modified,
                                record.turbo_rewrites_duration_s,
                                1 if record.is_turbo_rewrites else 0,
                            ),
                        )
                        conn.execute(
                            """
                            DELETE FROM execution_history
                            WHERE sequence NOT IN (
                                SELECT sequence FROM execution_history
                                ORDER BY sequence DESC
                                LIMIT 100
                            );
                            """
                        )
            except Exception as e:
                logging.error(f"Failed to add history record: {e}")

    def get_all(self) -> List[HistoryRecord]:
        """Retrieves all history records sorted by most recent first."""
        with self._lock:
            try:
                with self._get_conn() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, timestamp, mode, duration, status, total_channels, matched_channels, missing_channels, error_message, sources_stats_json, is_turbo, epg_stats_json, trigger, channels_modified, turbo_rewrites_duration_s, is_turbo_rewrites
                        FROM execution_history
                        ORDER BY sequence DESC
                        LIMIT 100;
                        """
                    )
                    rows = cursor.fetchall()
                    records = []
                    for r in rows:
                        try:
                            s_stats_raw = json.loads(r[9]) if r[9] else []
                            sources_stats = [SourceStats.model_validate(s) for s in s_stats_raw] if isinstance(s_stats_raw, list) else []
                        except Exception:
                            sources_stats = []

                        is_turbo = bool(r[10]) if len(r) > 10 and r[10] else False
                        try:
                            epg_stats_raw = json.loads(r[11]) if len(r) > 11 and r[11] else []
                            epg_stats = [EpgSourceStats.model_validate(s) for s in epg_stats_raw] if isinstance(epg_stats_raw, list) else []
                        except Exception:
                            epg_stats = []

                        trigger_val = str(r[12]) if len(r) > 12 and r[12] else "manual"
                        ch_mod = int(r[13]) if len(r) > 13 and r[13] is not None else 0
                        turbo_rw_dur = float(r[14]) if len(r) > 14 and r[14] is not None else 0.0
                        is_turbo_rw = bool(r[15]) if len(r) > 15 and r[15] is not None else False

                        records.append(
                            HistoryRecord(
                                id=r[0],
                                timestamp=r[1],
                                mode=r[2],
                                duration=r[3],
                                status=r[4],
                                total_channels=r[5],
                                matched_channels=r[6],
                                missing_channels=r[7],
                                error_message=r[8],
                                sources_stats=sources_stats,
                                is_turbo=is_turbo,
                                epg_stats=epg_stats,
                                trigger=trigger_val,
                                channels_modified=ch_mod,
                                turbo_rewrites_duration_s=turbo_rw_dur,
                                is_turbo_rewrites=is_turbo_rw,
                            )
                        )
                    return records
            except Exception as e:
                logging.error(f"Failed to get history records: {e}")
                return []

    def get_latest(self) -> Optional[HistoryRecord]:
        """Retrieves the most recent history record."""
        records = self.get_all()
        return records[0] if records else None

    def delete(self, record_id: str) -> bool:
        """Deletes a history record by ID."""
        with self._lock:
            try:
                with self._get_conn() as conn:
                    with conn:
                        cursor = conn.execute("DELETE FROM execution_history WHERE id = ?", (record_id,))
                        success = cursor.rowcount > 0
                return success
            except Exception as e:
                logging.error(f"Failed to delete history record '{record_id}': {e}")
                return False

    def clear_all(self) -> None:
        """Clears all execution history records."""
        with self._lock:
            try:
                with self._get_conn() as conn:
                    with conn:
                        conn.execute("DELETE FROM execution_history")
            except Exception as e:
                logging.error(f"Failed to clear execution history: {e}")
