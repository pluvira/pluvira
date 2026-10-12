"""Repository for managing IPTV M3U sources and XMLTV EPG sources in SQLite pluvira_main.db."""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from backend.config.models import Source, EPGSource, SourceSettings
from backend.core.db import db_manager
from backend.core.base_repository import BaseRepository
from backend.core.metadata_rule_repository import MetadataRuleRepository


class SourceRepository(BaseRepository):
    """Encapsulates SQLite operations for IPTV M3U and EPG sources."""

    table_name = "sources"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with target database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes sources, epg_sources, and metadata_rules tables."""
        db_manager.init_sources_table(conn)
        db_manager.init_epg_sources_table(conn)
        db_manager.init_metadata_rules_table(conn)

    # -------------------------------------------------------------------------
    # IPTV M3U Sources Operations
    # -------------------------------------------------------------------------

    def get_all_sources(self) -> List[Source]:
        """Retrieves all IPTV M3U sources ordered by priority sort_order.

        Returns:
            List[Source]: List of Source Pydantic models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, enabled, m3u_url, settings_json FROM sources ORDER BY sort_order ASC, rowid ASC"
            )
            sources: List[Source] = []
            grouped_rules = MetadataRuleRepository(db_path=self.db_path).get_all_source_rules_grouped()
            for name, enabled, m3u_url, settings_json in cursor.fetchall():
                settings: Optional[SourceSettings] = None
                if settings_json:
                    try:
                        data = json.loads(settings_json)
                        if data:
                            settings = SourceSettings.model_validate(data)
                    except Exception as e:
                        logging.warning(f"Failed to parse settings_json for source '{name}': {e}")
                if name in grouped_rules:
                    if settings is None:
                        settings = SourceSettings()
                    settings.rewrites = grouped_rules[name]
                elif settings:
                    settings.rewrites = []
                sources.append(
                    Source(
                        name=name,
                        enabled=bool(enabled),
                        m3u_url=m3u_url,
                        settings=settings,
                    )
                )
            return sources
        finally:
            conn.close()

    def get_source(self, name: str) -> Optional[Source]:
        """Retrieves a single IPTV M3U source by unique name.

        Args:
            name (str): IPTV source provider name.

        Returns:
            Optional[Source]: Source model if found, None otherwise.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, enabled, m3u_url, settings_json FROM sources WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            s_name, enabled, m3u_url, settings_json = row
            settings: Optional[SourceSettings] = None
            if settings_json:
                try:
                    data = json.loads(settings_json)
                    if data:
                        settings = SourceSettings.model_validate(data)
                except Exception:
                    pass
            src_rules = MetadataRuleRepository(db_path=self.db_path).get_source_rules(s_name)
            if src_rules:
                if settings is None:
                    settings = SourceSettings()
                settings.rewrites = src_rules
            elif settings:
                settings.rewrites = []
            return Source(
                name=s_name,
                enabled=bool(enabled),
                m3u_url=m3u_url,
                settings=settings,
            )
        finally:
            conn.close()

    def save_source(self, source: Source, sort_order: Optional[int] = None) -> None:
        """Saves or updates an IPTV M3U source atomically.

        Args:
            source (Source): Source model to persist.
            sort_order (Optional[int]): Sequential sort order. If None and existing,
                preserves current position. If None and new, appends at end.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sort_order FROM sources WHERE name = ?", (source.name,))
                row = cursor.fetchone()
                if row is not None:
                    actual_sort = row[0] if sort_order is None else sort_order
                else:
                    if sort_order is None:
                        cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM sources")
                        actual_sort = cursor.fetchone()[0]
                    else:
                        actual_sort = sort_order

                settings_json = "{}"
                if source.settings:
                    settings_dict = source.settings.model_dump(exclude_none=True)
                    settings_dict.pop("rewrites", None)
                    settings_json = json.dumps(settings_dict)
                    if source.settings.rewrites is not None:
                        MetadataRuleRepository(db_path=self.db_path).set_source_rules(
                            source.name, source.settings.rewrites
                        )

                conn.execute(
                    """
                    INSERT INTO sources (name, enabled, m3u_url, settings_json, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        enabled = excluded.enabled,
                        m3u_url = excluded.m3u_url,
                        settings_json = excluded.settings_json,
                        sort_order = excluded.sort_order;
                    """,
                    (
                        source.name,
                        1 if getattr(source, "enabled", True) else 0,
                        source.m3u_url,
                        settings_json,
                        actual_sort,
                    ),
                )
        finally:
            conn.close()

    def delete_source(self, name: str) -> bool:
        """Deletes an IPTV M3U source by name.

        Args:
            name (str): Target source name.

        Returns:
            bool: True if source was deleted, False if not found.
        """
        conn = self.get_conn()
        try:
            with conn:
                MetadataRuleRepository(db_path=self.db_path).delete_by_source(name)
                cursor = conn.execute("DELETE FROM sources WHERE name = ?", (name,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def reorder_sources(self, ordered_names: List[str]) -> None:
        """Sequentially reorders IPTV M3U sources matching the provided names list.

        Args:
            ordered_names (List[str]): Ordered list of source names.
        """
        conn = self.get_conn()
        try:
            with conn:
                for idx, name in enumerate(ordered_names):
                    conn.execute("UPDATE sources SET sort_order = ? WHERE name = ?", (idx, name))
        finally:
            conn.close()

    def get_active_sources_count(self) -> int:
        """Returns the count of currently enabled IPTV M3U sources.

        Returns:
            int: Number of active M3U sources.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sources WHERE enabled = 1")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def bulk_save_sources(self, sources: List[Source]) -> int:
        """Bulk inserts or updates multiple IPTV M3U sources in a single transaction.

        Args:
            sources (List[Source]): List of source models.

        Returns:
            int: Count of sources saved.
        """
        conn = self.get_conn()
        try:
            with conn:
                for idx, source in enumerate(sources):
                    settings_json = "{}"
                    if source.settings:
                        settings_dict = source.settings.model_dump(exclude_none=True)
                        settings_dict.pop("rewrites", None)
                        settings_json = json.dumps(settings_dict)
                        if source.settings.rewrites is not None:
                            MetadataRuleRepository(db_path=self.db_path).set_source_rules(
                                source.name, source.settings.rewrites
                            )
                    conn.execute(
                        """
                        INSERT INTO sources (name, enabled, m3u_url, settings_json, sort_order)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            enabled = excluded.enabled,
                            m3u_url = excluded.m3u_url,
                            settings_json = excluded.settings_json,
                            sort_order = excluded.sort_order;
                        """,
                        (
                            source.name,
                            1 if getattr(source, "enabled", True) else 0,
                            source.m3u_url,
                            settings_json,
                            idx,
                        ),
                    )
            return len(sources)
        finally:
            conn.close()

    def clear_all_sources(self) -> None:
        """Truncates the sources table."""
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM metadata_rules WHERE tier = 'source'")
                conn.execute("DELETE FROM sources")
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # XMLTV EPG Sources Operations
    # -------------------------------------------------------------------------

    def get_all_epg_sources(self) -> List[EPGSource]:
        """Retrieves all XMLTV EPG sources ordered by priority sort_order.

        Returns:
            List[EPGSource]: List of EPGSource Pydantic models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, enabled, url, user_agent FROM epg_sources ORDER BY sort_order ASC, rowid ASC"
            )
            epg_sources: List[EPGSource] = []
            for name, enabled, url, user_agent in cursor.fetchall():
                epg_sources.append(
                    EPGSource(
                        name=name,
                        enabled=bool(enabled),
                        url=url,
                        user_agent=user_agent if user_agent else None,
                    )
                )
            return epg_sources
        finally:
            conn.close()

    def get_epg_source(self, name: str) -> Optional[EPGSource]:
        """Retrieves a single XMLTV EPG source by unique name.

        Args:
            name (str): EPG source provider name.

        Returns:
            Optional[EPGSource]: EPGSource model if found, None otherwise.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, enabled, url, user_agent FROM epg_sources WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            s_name, enabled, url, user_agent = row
            return EPGSource(
                name=s_name,
                enabled=bool(enabled),
                url=url,
                user_agent=user_agent if user_agent else None,
            )
        finally:
            conn.close()

    def save_epg_source(self, epg_source: EPGSource, sort_order: Optional[int] = None) -> None:
        """Saves or updates an XMLTV EPG source atomically.

        Args:
            epg_source (EPGSource): EPG source model to persist.
            sort_order (Optional[int]): Sequential sort order.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sort_order FROM epg_sources WHERE name = ?", (epg_source.name,))
                row = cursor.fetchone()
                if row is not None:
                    actual_sort = row[0] if sort_order is None else sort_order
                else:
                    if sort_order is None:
                        cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM epg_sources")
                        actual_sort = cursor.fetchone()[0]
                    else:
                        actual_sort = sort_order

                conn.execute(
                    """
                    INSERT INTO epg_sources (name, enabled, url, user_agent, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        enabled = excluded.enabled,
                        url = excluded.url,
                        user_agent = excluded.user_agent,
                        sort_order = excluded.sort_order;
                    """,
                    (
                        epg_source.name,
                        1 if getattr(epg_source, "enabled", True) else 0,
                        epg_source.url,
                        epg_source.user_agent,
                        actual_sort,
                    ),
                )
        finally:
            conn.close()

    def delete_epg_source(self, name: str) -> bool:
        """Deletes an XMLTV EPG source by name.

        Args:
            name (str): Target EPG source name.

        Returns:
            bool: True if source was deleted, False if not found.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM epg_sources WHERE name = ?", (name,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def reorder_epg_sources(self, ordered_names: List[str]) -> None:
        """Sequentially reorders XMLTV EPG sources matching the provided names list.

        Args:
            ordered_names (List[str]): Ordered list of EPG source names.
        """
        conn = self.get_conn()
        try:
            with conn:
                for idx, name in enumerate(ordered_names):
                    conn.execute("UPDATE epg_sources SET sort_order = ? WHERE name = ?", (idx, name))
        finally:
            conn.close()

    def get_active_epg_sources_count(self) -> int:
        """Returns the count of currently enabled XMLTV EPG sources.

        Returns:
            int: Number of active EPG sources.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM epg_sources WHERE enabled = 1")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def bulk_save_epg_sources(self, epg_sources: List[EPGSource]) -> int:
        """Bulk inserts or updates multiple XMLTV EPG sources in a single transaction.

        Args:
            epg_sources (List[EPGSource]): List of EPG source models.

        Returns:
            int: Count of EPG sources saved.
        """
        conn = self.get_conn()
        try:
            with conn:
                for idx, epg_src in enumerate(epg_sources):
                    conn.execute(
                        """
                        INSERT INTO epg_sources (name, enabled, url, user_agent, sort_order)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            enabled = excluded.enabled,
                            url = excluded.url,
                            user_agent = excluded.user_agent,
                            sort_order = excluded.sort_order;
                        """,
                        (
                            epg_src.name,
                            1 if getattr(epg_src, "enabled", True) else 0,
                            epg_src.url,
                            epg_src.user_agent,
                            idx,
                        ),
                    )
            return len(epg_sources)
        finally:
            conn.close()

    def clear_all_epg_sources(self) -> None:
        """Truncates the epg_sources table."""
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM epg_sources")
        finally:
            conn.close()
