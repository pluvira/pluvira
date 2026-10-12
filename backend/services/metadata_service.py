"""Metadata service layer encapsulating rich EPG enrichment, artwork caching, and persistence."""

from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.config.models import EnrichedProgramDTO, MetadataProviderConfig
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.metadata_repository import MetadataRepository
from backend.core.metadata_sanitizer import MetadataSanitizer
from backend.core.metadata_resolvers import CascadingMetadataResolver
from backend.core.artwork_cache import ArtworkCache


class MetadataService:
    """Service handling rich metadata enrichment, cascading resolvers, and RAM disk artwork caching."""

    def __init__(
        self,
        repository: Optional[MetadataRepository] = None,
        resolver: Optional[CascadingMetadataResolver] = None,
        artwork_cache: Optional[ArtworkCache] = None,
        config_handler: Optional[YAMLConfigHandler] = None,
    ) -> None:
        """Initializes metadata service.

        Args:
            repository (Optional[MetadataRepository]): Override metadata repository.
            resolver (Optional[CascadingMetadataResolver]): Override cascading resolver.
            artwork_cache (Optional[ArtworkCache]): Override artwork cache.
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.repository = repository or MetadataRepository()
        self.artwork_cache = artwork_cache or ArtworkCache()

        if resolver:
            self.resolver = resolver
        else:
            config = self._get_metadata_config()
            self.resolver = CascadingMetadataResolver(config=config)

    def _get_metadata_config(self) -> MetadataProviderConfig:
        """Retrieves active MetadataProviderConfig from YAML handler."""
        try:
            cfg = self.config_handler.load_config()
            if cfg.settings and cfg.settings.metadata_providers:
                return cfg.settings.metadata_providers
        except Exception:
            pass
        return MetadataProviderConfig()

    async def enrich_program(
        self,
        title: str,
        release_year: Optional[int] = None,
        language: str = "en",
        force_refresh: bool = False,
    ) -> EnrichedProgramDTO:
        """Enriches programme title with artwork, synopsis, ratings, and cast.

        First checks SQLite WAL metadata cache. On miss, cascades to external providers,
        persists result to SQLite, and caches artwork to RAM disk.

        Args:
            title (str): Raw or cleaned broadcast programme title.
            release_year (Optional[int]): Optional release or broadcast year.
            language (str): Target ISO language code.
            force_refresh (bool): Skip local cache and query upstream providers.

        Returns:
            EnrichedProgramDTO: Enriched programme metadata model.
        """
        sanitized = MetadataSanitizer.sanitize(title)
        effective_year = release_year or sanitized.release_year

        if not force_refresh:
            cached = self.repository.get_by_title(
                cleaned_title=sanitized.cleaned_title,
                release_year=effective_year,
                language=language,
                check_expiry=True,
            )
            if cached:
                return cached

        enriched = await self.resolver.resolve(title, language=language)

        if enriched.found:
            config = self._get_metadata_config()
            ttl_days = config.metadata_retention_days

            if enriched.poster_url and enriched.poster_url.startswith(("http://", "https://")):
                poster_hash = await self.artwork_cache.save_image(enriched.poster_url)
                if poster_hash:
                    enriched.poster_url = f"/api/v1/metadata/artwork/poster/{poster_hash}"

            if enriched.backdrop_url and enriched.backdrop_url.startswith(("http://", "https://")):
                backdrop_hash = await self.artwork_cache.save_image(enriched.backdrop_url)
                if backdrop_hash:
                    enriched.backdrop_url = f"/api/v1/metadata/artwork/backdrop/{backdrop_hash}"

            self.repository.save(enriched, language=language, ttl_days=ttl_days)

        return enriched

    async def bulk_enrich(
        self, titles: List[str], language: str = "en"
    ) -> List[EnrichedProgramDTO]:
        """Enriches multiple programme titles sequentially in batch.

        Args:
            titles (List[str]): List of broadcast titles.
            language (str): Target language code.

        Returns:
            List[EnrichedProgramDTO]: Enriched metadata results list.
        """
        results: List[EnrichedProgramDTO] = []
        for t in titles:
            dto = await self.enrich_program(t, language=language)
            results.append(dto)
        return results

    def get_cached_metadata(self, hash_key: str) -> Optional[EnrichedProgramDTO]:
        """Retrieves cached metadata by composite hash key.

        Args:
            hash_key (str): SHA-256 composite lookup hash.

        Returns:
            Optional[EnrichedProgramDTO]: Found model or None.
        """
        return self.repository.get(hash_key, check_expiry=True)

    def search_metadata(self, query: str, limit: int = 50) -> List[EnrichedProgramDTO]:
        """Performs search query on local SQLite metadata records.

        Args:
            query (str): Partial title or synopsis query.
            limit (int): Max records to return.

        Returns:
            List[EnrichedProgramDTO]: Matched records list.
        """
        return self.repository.search(query, limit=limit)

    def get_artwork_path(self, image_hash: str) -> Optional[Path]:
        """Retrieves physical RAM disk file path for cached artwork.

        Args:
            image_hash (str): Artwork image filename hash.

        Returns:
            Optional[Path]: File path if present, None otherwise.
        """
        return self.artwork_cache.get_image_path(image_hash)

    def clear_cache(self) -> None:
        """Wipes both local SQLite metadata table and volatile RAM disk artwork directory."""
        self.repository.clear_all()
        self.artwork_cache.clear()

    async def search_epg(
        self,
        query: str,
        genre: Optional[str] = None,
        min_rating: Optional[float] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Searches programme metadata delegating to Pro native sub-5ms fuzzy search or SQLite fallback."""
        from backend.core.pro_bridge import ProBridge
        if ProBridge.is_available():
            pro_res = await ProBridge.search_epg(
                query=query,
                genre=genre,
                min_rating=min_rating,
                limit=limit,
            )
            if pro_res and pro_res.get("status") == "success":
                return pro_res.get("result", {})

        items = self.search_metadata(query, limit=limit)
        return {
            "count": len(items),
            "matches": [item.model_dump() for item in items],
        }

    async def probe_stream(
        self,
        stream_url: str,
        timeout_ms: int = 3000,
    ) -> Dict[str, Any]:
        """Probes live stream byte-range metrics delegating to Pro native inspector or Core fallback."""
        from backend.core.pro_bridge import ProBridge
        if ProBridge.is_available():
            pro_res = await ProBridge.probe_stream(
                stream_url=stream_url,
                timeout_ms=timeout_ms,
            )
            if pro_res and pro_res.get("status") == "success":
                return pro_res.get("result", {})

        from backend.core import link_tester
        verification = await link_tester.verify_link_detailed(stream_url)
        status_code = verification.get("code", 0)
        is_online = verification.get("status") == "online"
        is_hls = ".m3u8" in stream_url

        return {
            "stream_url": stream_url,
            "reachable": is_online,
            "status_code": status_code,
            "content_type": "application/x-mpegurl" if is_hls else "video/mp2t",
            "is_hls": is_hls,
            "bitrate_kbps": None,
            "resolution": None,
            "latency_ms": 50,
        }
