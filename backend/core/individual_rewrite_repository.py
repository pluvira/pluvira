"""Repository for managing individual channel rewrite rules in SQLite pluvira_main.db."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

from backend.config.models import RewriteRule
from backend.core.db import db_manager
from backend.core.base_repository import BaseRepository


class IndividualRewriteRepository(BaseRepository):
    """Encapsulates SQLite operations for individual channel rewrite rules."""

    table_name = "individual_rewrites"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with database path.

        Args:
            db_path (Optional[Path]): Override path to SQLite database.
        """
        super().__init__(db_path=db_path)

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes individual rewrites table in SQLite."""
        db_manager.init_individual_rewrites_table(conn)

    def get_all_grouped(self) -> Dict[str, List[RewriteRule]]:
        """Retrieves all individual rewrite rules grouped by original_url.

        Returns:
            Dict[str, List[RewriteRule]]: Dictionary mapping original_url to list of RewriteRule models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT original_url, field, pattern, replacement, mode, enabled, description
                FROM individual_rewrites
                ORDER BY id ASC
                """
            )
            grouped: Dict[str, List[RewriteRule]] = {}
            for row in cursor.fetchall():
                orig_url, field, pattern, replacement, mode, enabled, desc = row
                rule = RewriteRule(
                    field=field,
                    pattern=pattern or "",
                    replacement=replacement,
                    mode=mode or "replace",
                    enabled=bool(enabled),
                    description=desc,
                )
                grouped.setdefault(orig_url, []).append(rule)
            return grouped
        finally:
            conn.close()

    def get_by_url(self, original_url: str) -> List[RewriteRule]:
        """Retrieves rewrite rules for a specific channel original_url.

        Args:
            original_url (str): Channel original URL identity key.

        Returns:
            List[RewriteRule]: List of RewriteRule models.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT field, pattern, replacement, mode, enabled, description
                FROM individual_rewrites
                WHERE original_url = ?
                ORDER BY id ASC
                """,
                (original_url,),
            )
            rules: List[RewriteRule] = []
            for row in cursor.fetchall():
                field, pattern, replacement, mode, enabled, desc = row
                rules.append(
                    RewriteRule(
                        field=field,
                        pattern=pattern or "",
                        replacement=replacement,
                        mode=mode or "replace",
                        enabled=bool(enabled),
                        description=desc,
                    )
                )
            return rules
        finally:
            conn.close()

    def get_urls_having_rewrites(self) -> Set[str]:
        """Retrieves set of all original_urls that have at least one rewrite rule.

        Returns:
            Set[str]: Set of original URLs.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT original_url FROM individual_rewrites")
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def set_rule(
        self,
        original_url: str,
        field: str,
        replacement: str,
        mode: str = "replace",
        pattern: str = "",
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> None:
        """Inserts or updates a rewrite rule for an original_url and field.

        Args:
            original_url (str): Channel original URL identity key.
            field (str): Target attribute field name.
            replacement (str): New replacement value.
            mode (str): Transformation mode ('replace', 'regex', etc.).
            pattern (str): Search pattern if mode is not replace.
            enabled (bool): Whether the rule is active.
            description (Optional[str]): Optional description note.
        """
        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO individual_rewrites (original_url, field, pattern, replacement, mode, enabled, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(original_url, field) DO UPDATE SET
                        pattern = excluded.pattern,
                        replacement = excluded.replacement,
                        mode = excluded.mode,
                        enabled = excluded.enabled,
                        description = excluded.description;
                    """,
                    (original_url, field, pattern, replacement, mode, 1 if enabled else 0, description),
                )
        finally:
            conn.close()

    def delete_rule(self, original_url: str, field: str) -> bool:
        """Deletes a specific rewrite rule for an original_url and field.

        Args:
            original_url (str): Channel original URL identity key.
            field (str): Target attribute field name.

        Returns:
            bool: True if a rule was deleted, False otherwise.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM individual_rewrites WHERE original_url = ? AND field = ?",
                    (original_url, field),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_by_url(self, original_url: str) -> int:
        """Deletes all rewrite rules for a specific channel original_url.

        Args:
            original_url (str): Channel original URL identity key.

        Returns:
            int: Number of deleted rules.
        """
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM individual_rewrites WHERE original_url = ?",
                    (original_url,),
                )
                return cursor.rowcount
        finally:
            conn.close()

    def bulk_set_field(
        self,
        original_urls: List[str],
        field: str,
        replacement: str,
        mode: str = "replace",
        enabled: bool = True,
    ) -> int:
        """Assigns or updates a field value in bulk across multiple original_urls.

        Args:
            original_urls (List[str]): List of channel original URLs.
            field (str): Target attribute field name.
            replacement (str): New replacement value.
            mode (str): Transformation mode.
            enabled (bool): Rule enabled status.

        Returns:
            int: Count of rules updated or inserted.
        """
        if not original_urls:
            return 0

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.cursor()
                params = [
                    (url, field, "", replacement, mode, 1 if enabled else 0, None)
                    for url in original_urls
                ]
                cursor.executemany(
                    """
                    INSERT INTO individual_rewrites (original_url, field, pattern, replacement, mode, enabled, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(original_url, field) DO UPDATE SET
                        pattern = excluded.pattern,
                        replacement = excluded.replacement,
                        mode = excluded.mode,
                        enabled = excluded.enabled,
                        description = excluded.description;
                    """,
                    params,
                )
                return len(original_urls)
        finally:
            conn.close()

    def bulk_delete_by_urls(self, original_urls: List[str]) -> int:
        """Deletes all rewrite rules for target original_urls in bulk.

        Args:
            original_urls (List[str]): List of channel original URLs.

        Returns:
            int: Number of deleted rules.
        """
        if not original_urls:
            return 0

        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    f"DELETE FROM individual_rewrites WHERE original_url IN ({','.join('?' for _ in original_urls)})",
                    original_urls,
                )
                return cursor.rowcount
        finally:
            conn.close()


