"""Repository for managing enriched EPG metadata in SQLite pluvira_metadata.db."""

import json
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.config.models import EnrichedProgramDTO, CastMemberDTO
from backend.core.db import DatabaseManager
from backend.core.base_repository import BaseRepository


class MetadataRepository(BaseRepository):
    """Encapsulates SQLite operations for programme metadata with TTL caching and composite indexing."""

    table_name = "programme_metadata"
    db_type = "metadata"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initializes repository with target metadata database path.

        Args:
            db_path (Optional[Path]): Override path to pluvira_metadata.db SQLite database.
        """
        super().__init__(db_path=db_path, table_name="programme_metadata", db_type="metadata")

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes metadata tables in SQLite pluvira_metadata.db."""
        DatabaseManager.init_metadata_tables(conn)

    @staticmethod
    def compute_hash_key(cleaned_title: str, release_year: Optional[int] = None, language: str = "en") -> str:
        """Computes deterministic SHA-256 composite lookup hash.

        Args:
            cleaned_title (str): Cleaned and normalized programme title.
            release_year (Optional[int]): Optional release or broadcast year.
            language (str): Language code.

        Returns:
            str: 64-character hexadecimal SHA-256 hash digest.
        """
        year_str = str(release_year) if release_year else ""
        raw_key = f"{cleaned_title.strip().lower()}::{year_str}::{language.strip().lower()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, hash_key: str, check_expiry: bool = True) -> Optional[EnrichedProgramDTO]:
        """Retrieves an enriched metadata record by composite hash key.

        Args:
            hash_key (str): SHA-256 composite hash key.
            check_expiry (bool): Whether to enforce TTL expiration check.

        Returns:
            Optional[EnrichedProgramDTO]: Populated model if found and active, None otherwise.
        """
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT hash_key, cleaned_title, original_title, release_year, language,
                       provider, overview, poster_url, backdrop_url, rating, vote_count,
                       genres_json, director, cast_json, external_url, expires_at
                FROM programme_metadata
                WHERE hash_key = ?;
                """,
                (hash_key,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            expires_at = row[15]
            if check_expiry and expires_at is not None:
                current_time = int(time.time())
                if current_time > expires_at:
                    return None

            try:
                genres = json.loads(row[11]) if row[11] else []
            except Exception:
                genres = []

            try:
                cast_raw = json.loads(row[13]) if row[13] else []
                cast_members = [CastMemberDTO(**c) if isinstance(c, dict) else CastMemberDTO(name=str(c)) for c in cast_raw]
            except Exception:
                cast_members = []

            return EnrichedProgramDTO(
                hash_key=row[0],
                title=row[1],
                original_title=row[2] or "",
                release_year=row[3],
                provider=row[5],
                overview=row[6] or "",
                poster_url=row[7] or "",
                backdrop_url=row[8] or "",
                rating=row[9],
                vote_count=row[10],
                genres=genres,
                director=row[12] or "",
                cast=cast_members,
                external_url=row[14] or "",
                found=True,
            )
        finally:
            conn.close()

    def get_by_title(
        self, cleaned_title: str, release_year: Optional[int] = None, language: str = "en", check_expiry: bool = True
    ) -> Optional[EnrichedProgramDTO]:
        """Retrieves enriched metadata by title, optional year, and language."""
        hash_key = self.compute_hash_key(cleaned_title, release_year, language)
        return self.get(hash_key, check_expiry=check_expiry)

    def save(self, dto: EnrichedProgramDTO, language: str = "en", ttl_days: Optional[int] = 30) -> str:
        """Saves or updates enriched programme metadata with TTL expiration."""
        hash_key = dto.hash_key or self.compute_hash_key(dto.title, dto.release_year, language)
        dto.hash_key = hash_key

        now_epoch = int(time.time())
        expires_at = now_epoch + (ttl_days * 86400) if ttl_days is not None else None

        genres_json = json.dumps(dto.genres or [])
        cast_dicts = [c.model_dump() for c in dto.cast] if dto.cast else []
        cast_json = json.dumps(cast_dicts)

        conn = self.get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO programme_metadata (
                        hash_key, cleaned_title, original_title, release_year, language,
                        provider, overview, poster_url, backdrop_url, rating, vote_count,
                        genres_json, director, cast_json, external_url, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    ON CONFLICT(hash_key) DO UPDATE SET
                        cleaned_title = excluded.cleaned_title,
                        original_title = excluded.original_title,
                        release_year = excluded.release_year,
                        language = excluded.language,
                        provider = excluded.provider,
                        overview = excluded.overview,
                        poster_url = excluded.poster_url,
                        backdrop_url = excluded.backdrop_url,
                        rating = excluded.rating,
                        vote_count = excluded.vote_count,
                        genres_json = excluded.genres_json,
                        director = excluded.director,
                        cast_json = excluded.cast_json,
                        external_url = excluded.external_url,
                        updated_at = CURRENT_TIMESTAMP,
                        expires_at = excluded.expires_at;
                    """,
                    (
                        hash_key,
                        dto.title,
                        dto.original_title or "",
                        dto.release_year,
                        language.strip().lower(),
                        dto.provider,
                        dto.overview or "",
                        dto.poster_url or "",
                        dto.backdrop_url or "",
                        dto.rating,
                        dto.vote_count,
                        genres_json,
                        dto.director or "",
                        cast_json,
                        dto.external_url or "",
                        expires_at,
                    ),
                )
            return hash_key
        finally:
            conn.close()

    def bulk_save(self, dtos: List[EnrichedProgramDTO], language: str = "en", ttl_days: Optional[int] = 30) -> int:
        """Bulk inserts or updates multiple enriched metadata DTOs in a single transaction."""
        if not dtos:
            return 0

        now_epoch = int(time.time())
        expires_at = now_epoch + (ttl_days * 86400) if ttl_days is not None else None

        records = []
        for dto in dtos:
            hash_key = dto.hash_key or self.compute_hash_key(dto.title, dto.release_year, language)
            dto.hash_key = hash_key
            genres_json = json.dumps(dto.genres or [])
            cast_dicts = [c.model_dump() for c in dto.cast] if dto.cast else []
            cast_json = json.dumps(cast_dicts)
            records.append((
                hash_key,
                dto.title,
                dto.original_title or "",
                dto.release_year,
                language.strip().lower(),
                dto.provider,
                dto.overview or "",
                dto.poster_url or "",
                dto.backdrop_url or "",
                dto.rating,
                dto.vote_count,
                genres_json,
                dto.director or "",
                cast_json,
                dto.external_url or "",
                expires_at,
            ))

        conn = self.get_conn()
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO programme_metadata (
                        hash_key, cleaned_title, original_title, release_year, language,
                        provider, overview, poster_url, backdrop_url, rating, vote_count,
                        genres_json, director, cast_json, external_url, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    ON CONFLICT(hash_key) DO UPDATE SET
                        cleaned_title = excluded.cleaned_title,
                        original_title = excluded.original_title,
                        release_year = excluded.release_year,
                        language = excluded.language,
                        provider = excluded.provider,
                        overview = excluded.overview,
                        poster_url = excluded.poster_url,
                        backdrop_url = excluded.backdrop_url,
                        rating = excluded.rating,
                        vote_count = excluded.vote_count,
                        genres_json = excluded.genres_json,
                        director = excluded.director,
                        cast_json = excluded.cast_json,
                        external_url = excluded.external_url,
                        updated_at = CURRENT_TIMESTAMP,
                        expires_at = excluded.expires_at;
                    """,
                    records,
                )
            return len(records)
        finally:
            conn.close()

    def search(self, query: str, limit: int = 50) -> List[EnrichedProgramDTO]:
        """Searches metadata records matching title or overview."""
        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            param = f"%{query.strip()}%"
            cursor.execute(
                """
                SELECT hash_key, cleaned_title, original_title, release_year, language,
                       provider, overview, poster_url, backdrop_url, rating, vote_count,
                       genres_json, director, cast_json, external_url, expires_at
                FROM programme_metadata
                WHERE cleaned_title LIKE ? OR overview LIKE ?
                ORDER BY rating DESC
                LIMIT ?;
                """,
                (param, param, limit),
            )
            results = []
            for row in cursor.fetchall():
                try:
                    genres = json.loads(row[11]) if row[11] else []
                except Exception:
                    genres = []

                try:
                    cast_raw = json.loads(row[13]) if row[13] else []
                    cast_members = [CastMemberDTO(**c) if isinstance(c, dict) else CastMemberDTO(name=str(c)) for c in cast_raw]
                except Exception:
                    cast_members = []

                results.append(
                    EnrichedProgramDTO(
                        hash_key=row[0],
                        title=row[1],
                        original_title=row[2] or "",
                        release_year=row[3],
                        provider=row[5],
                        overview=row[6] or "",
                        poster_url=row[7] or "",
                        backdrop_url=row[8] or "",
                        rating=row[9],
                        vote_count=row[10],
                        genres=genres,
                        director=row[12] or "",
                        cast=cast_members,
                        external_url=row[14] or "",
                        found=True,
                    )
                )
            return results
        finally:
            conn.close()

    def prune_expired(self) -> int:
        """Removes expired metadata records whose TTL has elapsed."""
        now_epoch = int(time.time())
        conn = self.get_conn()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM programme_metadata WHERE expires_at IS NOT NULL AND expires_at < ?;",
                    (now_epoch,),
                )
                return cursor.rowcount
        finally:
            conn.close()


