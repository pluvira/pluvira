"""Repository for managing global and source metadata rewrite rules in SQLite pluvira_main.db."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any

from backend.config.models import RewriteRule
from backend.core.db import db_manager


class MetadataRuleRepository:
    """Encapsulates SQLite operations for global and source metadata rewrite rules."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        self._custom_path = db_path

    @property
    def db_path(self) -> Path:
        """Resolves target database path dynamically.

        Returns:
            Path: Target SQLite database file path.
        """
        return db_manager.get_main_db_path(self._custom_path)

    def get_conn(self) -> sqlite3.Connection:
        """Opens and returns a SQLite connection with schema initialized.

        Returns:
            sqlite3.Connection: Database connection instance.
        """
        conn = db_manager.get_connection(self.db_path)
        db_manager.init_metadata_rules_table(conn)
        return conn

    def get_global_rules(self) -> List[RewriteRule]:
        """Retrieves all global metadata rewrite rules ordered by sort_order.

        Returns:
            List[RewriteRule]: List of global RewriteRule models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT field, pattern, replacement, mode, enabled, description
                FROM metadata_rules
                WHERE tier = 'global' OR is_global = 1
                ORDER BY sort_order ASC, id ASC
                """
            )
            rules: List[RewriteRule] = []
            for field, pattern, replacement, mode, enabled, description in cursor.fetchall():
                rules.append(
                    RewriteRule(
                        field=field,
                        pattern=pattern,
                        replacement=replacement,
                        mode=mode,
                        enabled=bool(enabled),
                        description=description,
                    )
                )
            return rules
        finally:
            conn.close()

    def set_global_rules(self, rules: List[RewriteRule]) -> None:
        """Atomically replaces all global metadata rewrite rules.

        Args:
            rules (List[RewriteRule]): Ordered list of global rewrite rules.
        """
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM metadata_rules WHERE tier = 'global' OR is_global = 1")
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
        finally:
            conn.close()

    def get_source_rules(self, source_name: str) -> List[RewriteRule]:
        """Retrieves all source metadata rewrite rules for a given source provider.

        Args:
            source_name (str): Target IPTV source name.

        Returns:
            List[RewriteRule]: List of source RewriteRule models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT field, pattern, replacement, mode, enabled, description
                FROM metadata_rules
                WHERE (tier = 'source' OR is_global = 0) AND source_name = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (source_name,),
            )
            rules: List[RewriteRule] = []
            for field, pattern, replacement, mode, enabled, description in cursor.fetchall():
                rules.append(
                    RewriteRule(
                        field=field,
                        pattern=pattern,
                        replacement=replacement,
                        mode=mode,
                        enabled=bool(enabled),
                        description=description,
                    )
                )
            return rules
        finally:
            conn.close()

    def set_source_rules(self, source_name: str, rules: List[RewriteRule]) -> None:
        """Atomically replaces all metadata rewrite rules for a specific source provider.

        Args:
            source_name (str): Target IPTV source name.
            rules (List[RewriteRule]): Ordered list of source rewrite rules.
        """
        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    "DELETE FROM metadata_rules WHERE (tier = 'source' OR is_global = 0) AND source_name = ?",
                    (source_name,),
                )
                for idx, r in enumerate(rules):
                    conn.execute(
                        """
                        INSERT INTO metadata_rules (
                            tier, is_global, source_name, field, pattern, replacement, mode, enabled, description, sort_order
                        ) VALUES ('source', 0, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_name,
                            r.field,
                            r.pattern or "",
                            r.replacement,
                            r.mode or "regex",
                            1 if r.enabled else 0,
                            r.description,
                            idx,
                        ),
                    )
        finally:
            conn.close()

    def get_all_source_rules_grouped(self) -> Dict[str, List[RewriteRule]]:
        """Retrieves all source metadata rewrite rules grouped by source_name in a single query.

        Returns:
            Dict[str, List[RewriteRule]]: Map of source_name to ordered list of RewriteRule models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_name, field, pattern, replacement, mode, enabled, description
                FROM metadata_rules
                WHERE tier = 'source' OR is_global = 0
                ORDER BY sort_order ASC, id ASC
                """
            )
            grouped: Dict[str, List[RewriteRule]] = {}
            for src_name, field, pattern, replacement, mode, enabled, description in cursor.fetchall():
                rule = RewriteRule(
                    field=field,
                    pattern=pattern,
                    replacement=replacement,
                    mode=mode,
                    enabled=bool(enabled),
                    description=description,
                )
                grouped.setdefault(src_name, []).append(rule)
            return grouped
        finally:
            conn.close()

    def delete_by_source(self, source_name: str) -> int:
        """Deletes all metadata rewrite rules for a specific source provider.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            int: Number of deleted rules.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM metadata_rules WHERE (tier = 'source' OR is_global = 0) AND source_name = ?",
                    (source_name,),
                )
                return cursor.rowcount
        finally:
            conn.close()

    def get_all_rules_flat(self) -> List[Dict[str, Any]]:
        """Retrieves all metadata rules as a flat list of dictionaries for backup export.

        Returns:
            List[Dict[str, Any]]: Flat list of rule records.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT tier, is_global, source_name, field, pattern, replacement, mode, enabled, description, sort_order
                FROM metadata_rules
                ORDER BY is_global DESC, tier ASC, source_name ASC, sort_order ASC, id ASC
                """
            )
            records: List[Dict[str, Any]] = []
            for tier, is_global, src_name, field, pattern, replacement, mode, enabled, description, sort_order in cursor.fetchall():
                records.append({
                    "tier": tier,
                    "is_global": is_global,
                    "source_name": src_name,
                    "field": field,
                    "pattern": pattern,
                    "replacement": replacement,
                    "mode": mode,
                    "enabled": bool(enabled),
                    "description": description,
                    "sort_order": sort_order,
                })
            return records
        finally:
            conn.close()

    def bulk_set_all(self, items: List[Dict[str, Any]]) -> int:
        """Bulk inserts or replaces metadata rules from raw dictionary items.

        Args:
            items (List[Dict[str, Any]]): List of rule dictionaries.

        Returns:
            int: Count of inserted records.
        """
        conn = self.get_conn()
        try:
            with conn:
                inserted = 0
                for item in items:
                    tier = item.get("tier", "global")
                    is_global = 1 if (item.get("is_global") is True or item.get("is_global") == 1 or tier == "global") else 0
                    src_name = item.get("source_name", "")
                    field = item.get("field", "name")
                    pattern = item.get("pattern", "")
                    replacement = item.get("replacement", "")
                    mode = item.get("mode", "regex")
                    enabled = 1 if item.get("enabled", True) else 0
                    desc = item.get("description")
                    sort_order = item.get("sort_order", 0)

                    conn.execute(
                        """
                        INSERT INTO metadata_rules (
                            tier, is_global, source_name, field, pattern, replacement, mode, enabled, description, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (tier, is_global, src_name, field, pattern, replacement, mode, enabled, desc, sort_order),
                    )
                    inserted += 1
                return inserted
        finally:
            conn.close()

    def clear_all(self) -> None:
        """Truncates the metadata_rules table."""
        conn = self.get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM metadata_rules")
        finally:
            conn.close()

    def get_count(self, tier: Optional[str] = None) -> int:
        """Returns the total number of rules stored, optionally filtered by tier.

        Args:
            tier (Optional[str]): Optional tier filter ('global' or 'source').

        Returns:
            int: Total record count.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            if tier == "global":
                cursor.execute("SELECT COUNT(*) FROM metadata_rules WHERE tier = 'global' OR is_global = 1")
            elif tier == "source":
                cursor.execute("SELECT COUNT(*) FROM metadata_rules WHERE tier = 'source' OR is_global = 0")
            elif tier:
                cursor.execute("SELECT COUNT(*) FROM metadata_rules WHERE tier = ?", (tier,))
            else:
                cursor.execute("SELECT COUNT(*) FROM metadata_rules")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def seed_default_rules_if_empty(self) -> int:
        """Seeds default global rewrite rules if no global rules currently exist.

        Returns:
            int: Number of default rules seeded.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata_rules WHERE tier = 'global' OR is_global = 1")
            if cursor.fetchone()[0] == 0:
                from backend.config.defaults import get_default_global_rules
                rules = get_default_global_rules()
                self.set_global_rules(rules)
                return len(rules)
            return 0
        finally:
            conn.close()
