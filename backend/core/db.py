"""Database connection and initialization manager using SQLite WAL mode."""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from backend.config.settings import settings


class DatabaseManager:
    """Manages thread-safe SQLite connections with WAL mode and PRAGMA optimizations."""

    _lock = threading.RLock()

    @staticmethod
    def get_main_db_path(custom_path: Optional[Path] = None) -> Path:
        """Resolves target pluvira_main.db database file path dynamically."""
        if custom_path is not None:
            return custom_path
        return settings.data_dir / "pluvira_main.db"

    @staticmethod
    def get_epg_db_path(custom_path: Optional[Path] = None) -> Path:
        """Resolves target pluvira_epg.db database file path dynamically."""
        if custom_path is not None:
            return custom_path
        return settings.data_dir / "pluvira_epg.db"

    @staticmethod
    def get_metadata_db_path(custom_path: Optional[Path] = None) -> Path:
        """Resolves target pluvira_metadata.db database file path dynamically."""
        if custom_path is not None:
            return custom_path
        return settings.data_dir / "pluvira_metadata.db"

    @staticmethod
    def get_db_path(custom_path: Optional[Path] = None) -> Path:
        """Resolves target SQLite database file path dynamically.

        Args:
            custom_path (Optional[Path]): Override database file path.

        Returns:
            Path: Resolved database file path.
        """
        if custom_path is not None:
            return custom_path
        return settings.data_dir / "pluvira_main.db"

    @classmethod
    def get_connection(cls, db_path: Optional[Path] = None) -> sqlite3.Connection:
        """Opens a thread-safe SQLite connection with WAL mode enabled.

        Args:
            db_path (Optional[Path]): Target database file path.

        Returns:
            sqlite3.Connection: Configured SQLite connection instance.
        """
        target_path = cls.get_db_path(db_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(target_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @classmethod
    def init_all_main_tables(cls, conn: sqlite3.Connection) -> None:
        """Initializes all pluvira_main.db relational tables atomically."""
        with cls._lock:
            cls.init_cloud_identity_table(conn)
            cls.init_individual_rewrites_table(conn)
            cls.init_channel_merges_table(conn)
            cls.init_epg_overrides_table(conn)
            cls.init_source_channel_filters_table(conn)
            cls.init_sources_table(conn)
            cls.init_epg_sources_table(conn)
            cls.init_metadata_rules_table(conn)
            cls.init_notification_tables(conn)
            cls.init_bulletin_tables(conn)
            cls.seed_default_metadata_rules(conn)

    @classmethod
    def init_cloud_identity_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the cloud_identity table exists in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cloud_identity (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    uid TEXT NOT NULL,
                    formatted_id TEXT NOT NULL,
                    access_token TEXT,
                    license_token TEXT,
                    device_hash TEXT,
                    linked_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    @classmethod
    def get_cloud_identity(cls, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Retrieves linked cloud identity record from pluvira_main.db."""
        conn = cls.get_connection(db_path)
        try:
            cls.init_cloud_identity_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT uid, formatted_id, access_token, license_token, device_hash, linked_at FROM cloud_identity WHERE id = 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "uid": row[0],
                "formatted_id": row[1],
                "access_token": row[2],
                "license_token": row[3],
                "device_hash": row[4],
                "linked_at": row[5],
                "is_linked": True,
            }
        finally:
            conn.close()

    @classmethod
    def save_cloud_identity(
        cls,
        uid: str,
        formatted_id: str,
        access_token: Optional[str] = None,
        license_token: Optional[str] = None,
        device_hash: Optional[str] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        """Stores or updates the singleton cloud identity record in pluvira_main.db."""
        clean_at = access_token.strip() if access_token and access_token.strip() else None
        clean_lt = license_token.strip() if license_token and license_token.strip() else None
        clean_dh = device_hash.strip() if device_hash and device_hash.strip() else None
        conn = cls.get_connection(db_path)
        try:
            cls.init_cloud_identity_table(conn)
            now_iso = datetime.now(timezone.utc).isoformat()
            with cls._lock, conn:
                conn.execute(
                    """
                    INSERT INTO cloud_identity (id, uid, formatted_id, access_token, license_token, device_hash, linked_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        uid = excluded.uid,
                        formatted_id = excluded.formatted_id,
                        access_token = COALESCE(excluded.access_token, cloud_identity.access_token),
                        license_token = COALESCE(excluded.license_token, cloud_identity.license_token),
                        device_hash = COALESCE(excluded.device_hash, cloud_identity.device_hash),
                        linked_at = excluded.linked_at;
                    """,
                    (uid, formatted_id, clean_at, clean_lt, clean_dh, now_iso),
                )
        finally:
            conn.close()

    @classmethod
    def clear_cloud_identity(cls, db_path: Optional[Path] = None) -> None:
        """Clears linked cloud identity record from pluvira_main.db."""
        conn = cls.get_connection(db_path)
        try:
            cls.init_cloud_identity_table(conn)
            with cls._lock, conn:
                conn.execute("DELETE FROM cloud_identity WHERE id = 1;")
        finally:
            conn.close()


    @classmethod
    def init_individual_rewrites_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the individual_rewrites table and index exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS individual_rewrites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_url TEXT NOT NULL,
                    field TEXT NOT NULL,
                    pattern TEXT NOT NULL DEFAULT '',
                    replacement TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'replace',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(original_url, field)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_individual_rewrites_url
                ON individual_rewrites(original_url);
                """
            )
            conn.commit()


    @classmethod
    def init_channel_merges_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the channel_merges and channel_merge_backups tables exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_merges (
                    master_name TEXT PRIMARY KEY,
                    name TEXT,
                    epg_id TEXT,
                    logo TEXT,
                    group_title TEXT,
                    user_agent TEXT,
                    primary_url TEXT NOT NULL,
                    primary_source TEXT NOT NULL,
                    primary_user_agent TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_merge_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    master_name TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    user_agent TEXT,
                    FOREIGN KEY(master_name) REFERENCES channel_merges(master_name) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_channel_merge_backups_master
                ON channel_merge_backups(master_name);
                """
            )
            conn.commit()

    @classmethod
    def init_epg_overrides_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the epg_mapping_overrides table and indexes exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS epg_mapping_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT NOT NULL,
                    epg_id TEXT NOT NULL,
                    source_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_name, source_name)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_epg_overrides_channel
                ON epg_mapping_overrides(channel_name);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_epg_overrides_source
                ON epg_mapping_overrides(source_name);
                """
            )
            conn.commit()


    @classmethod
    def init_source_channel_filters_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the source_channel_filters table and indexes exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_channel_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    filter_type TEXT NOT NULL CHECK(filter_type IN ('allow', 'deny')),
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_name, channel_name, filter_type)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_filters_lookup
                ON source_channel_filters(source_name, filter_type);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_filters_channel
                ON source_channel_filters(channel_name);
                """
            )
            conn.commit()


    @classmethod
    def init_sources_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the sources table and index exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    name TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    m3u_url TEXT NOT NULL,
                    settings_json TEXT DEFAULT '{}',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sources_sort_order
                ON sources(sort_order);
                """
            )
            conn.commit()

    @classmethod
    def init_epg_sources_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the epg_sources table and index exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS epg_sources (
                    name TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    url TEXT NOT NULL,
                    user_agent TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_epg_sources_sort_order
                ON epg_sources(sort_order);
                """
            )
            conn.commit()


    @classmethod
    def init_metadata_rules_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the metadata_rules table and indexes exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier TEXT NOT NULL DEFAULT 'global' CHECK(tier IN ('global', 'source')),
                    is_global INTEGER NOT NULL DEFAULT 1,
                    source_name TEXT NOT NULL DEFAULT '',
                    field TEXT NOT NULL,
                    pattern TEXT NOT NULL DEFAULT '',
                    replacement TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'regex',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    description TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(metadata_rules);")
            columns = {row[1] for row in cursor.fetchall()}
            if "is_global" not in columns:
                conn.execute("ALTER TABLE metadata_rules ADD COLUMN is_global INTEGER NOT NULL DEFAULT 1;")
            if "tier" not in columns:
                conn.execute("ALTER TABLE metadata_rules ADD COLUMN tier TEXT NOT NULL DEFAULT 'global';")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metadata_rules_lookup
                ON metadata_rules(tier, source_name, sort_order);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metadata_rules_global
                ON metadata_rules(is_global, source_name, sort_order);
                """
            )
            conn.commit()

    @classmethod
    def seed_default_metadata_rules(cls, conn: sqlite3.Connection) -> int:
        """Seeds default global rewrite rules if no global rules exist."""
        with cls._lock:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata_rules WHERE tier = 'global'")
            if cursor.fetchone()[0] == 0:
                from backend.config.defaults import get_default_global_rules
                rules = get_default_global_rules()
                for idx, r in enumerate(rules):
                    conn.execute(
                        """
                        INSERT INTO metadata_rules (
                            tier, is_global, source_name, field, pattern, replacement, mode, enabled, description, sort_order
                        ) VALUES ('global', 1, '', ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r.field,
                            r.pattern or "",
                            r.replacement,
                            r.mode or "regex",
                            1 if r.enabled else 0,
                            r.description,
                            idx,
                        ),
                    )
                conn.commit()
                return len(rules)
            return 0

    @classmethod
    def init_notification_tables(cls, conn: sqlite3.Connection) -> None:
        """Ensures the notification_settings and notification_targets tables exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    events_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()


    @classmethod
    def init_metadata_tables(cls, conn: sqlite3.Connection) -> None:
        """Ensures the programme_metadata table and indexes exist in pluvira_metadata.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS programme_metadata (
                    hash_key TEXT PRIMARY KEY,
                    cleaned_title TEXT NOT NULL,
                    original_title TEXT,
                    release_year INTEGER,
                    language TEXT NOT NULL DEFAULT 'en',
                    provider TEXT NOT NULL,
                    overview TEXT,
                    poster_url TEXT,
                    backdrop_url TEXT,
                    rating REAL,
                    vote_count INTEGER,
                    genres_json TEXT DEFAULT '[]',
                    director TEXT,
                    cast_json TEXT DEFAULT '[]',
                    external_url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at INTEGER
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_programme_metadata_title
                ON programme_metadata(cleaned_title, release_year);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_programme_metadata_expires
                ON programme_metadata(expires_at);
                """
            )
            conn.commit()


    @classmethod
    def init_bulletin_tables(cls, conn: sqlite3.Connection) -> None:
        """Ensures the system_bulletins and bulletin_sync_queue tables exist in pluvira_main.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_bulletins (
                    id TEXT PRIMARY KEY,
                    level TEXT NOT NULL DEFAULT 'info',
                    icon TEXT,
                    title_json TEXT NOT NULL,
                    message_json TEXT NOT NULL,
                    action_label_json TEXT,
                    action_url TEXT,
                    media_json TEXT,
                    dismissible INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 0,
                    expires_at INTEGER NOT NULL,
                    signature TEXT,
                    is_dismissed INTEGER NOT NULL DEFAULT 0,
                    dismissed_at TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    read_at TEXT,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(system_bulletins);")
            columns = {row[1] for row in cursor.fetchall()}
            if "is_read" not in columns:
                conn.execute("ALTER TABLE system_bulletins ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0;")
            if "read_at" not in columns:
                conn.execute("ALTER TABLE system_bulletins ADD COLUMN read_at TEXT;")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_system_bulletins_active
                ON system_bulletins (is_dismissed, expires_at);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bulletin_sync_queue (
                    bulletin_id TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK(event_type IN ('received', 'read', 'dismissed')),
                    queued_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (bulletin_id, event_type)
                );
                """
            )
            conn.commit()

    @classmethod
    def init_processed_channels_table(cls, conn: sqlite3.Connection) -> None:
        """Ensures the processed_channels table and indexes exist in pluvira_epg.db."""
        with cls._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_channels (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    group_name TEXT,
                    logo TEXT,
                    tvg_id TEXT,
                    extinf TEXT,
                    user_agent TEXT,
                    force_proxy INTEGER DEFAULT 0,
                    is_modified INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(processed_channels);")
            columns = {row[1] for row in cursor.fetchall()}
            if "tvg_id" not in columns:
                conn.execute("ALTER TABLE processed_channels ADD COLUMN tvg_id TEXT;")
            if "extinf" not in columns:
                conn.execute("ALTER TABLE processed_channels ADD COLUMN extinf TEXT;")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_proc_ch_source
                ON processed_channels(source);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_proc_ch_orig_url
                ON processed_channels(original_url);
                """
            )
            conn.commit()


db_manager = DatabaseManager()
