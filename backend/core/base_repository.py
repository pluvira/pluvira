"""Base repository class providing standardized SQLite connection and lifecycle operations."""

import sqlite3
from pathlib import Path
from typing import Optional

from backend.core.db import DatabaseManager


class BaseRepository:
    """Base repository encapsulating common SQLite operations and schema lifecycle."""

    table_name: str = ""
    db_type: str = "main"
    _custom_db_path: Optional[Path] = None

    def __init__(
        self,
        db_path: Optional[Path] = None,
        table_name: Optional[str] = None,
        db_type: Optional[str] = None,
    ) -> None:
        """Initializes base repository with optional path and table name overrides.

        Args:
            db_path (Optional[Path]): Override path to SQLite database file.
            table_name (Optional[str]): Override table name for repository.
            db_type (Optional[str]): Database category ('main', 'epg', 'metadata').
        """
        self._custom_db_path = db_path
        if table_name is not None:
            self.table_name = table_name
        if db_type is not None:
            self.db_type = db_type
        conn = self.get_conn()
        conn.close()

    @property
    def db_path(self) -> Path:
        """Resolves target database path dynamically.

        Returns:
            Path: Target SQLite database file path.
        """
        custom = getattr(self, "_custom_db_path", None)
        if self.db_type == "metadata":
            return DatabaseManager.get_metadata_db_path(custom)
        elif self.db_type == "epg":
            return DatabaseManager.get_epg_db_path(custom)
        return DatabaseManager.get_main_db_path(custom)

    @db_path.setter
    def db_path(self, value: Optional[Path]) -> None:
        """Sets explicit database file path override.

        Args:
            value (Optional[Path]): New database path override.
        """
        self._custom_db_path = value

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Schema initialization hook to be implemented by subclasses.

        Args:
            conn (sqlite3.Connection): Database connection instance.
        """
        pass

    def get_conn(self) -> sqlite3.Connection:
        """Opens and returns a SQLite connection with schema initialized.

        Returns:
            sqlite3.Connection: Database connection instance.
        """
        conn = DatabaseManager.get_connection(self.db_path)
        self._init_schema(conn)
        return conn

    def clear_all(self) -> None:
        """Truncates the primary repository table."""
        if not self.table_name:
            raise NotImplementedError("table_name must be defined for clear_all()")
        conn = self.get_conn()
        try:
            with conn:
                conn.execute(f"DELETE FROM {self.table_name};")
        finally:
            conn.close()

    def get_count(self) -> int:
        """Returns total number of records stored in primary table.

        Returns:
            int: Total record count.
        """
        if not self.table_name:
            raise NotImplementedError("table_name must be defined for get_count()")
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name};")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
