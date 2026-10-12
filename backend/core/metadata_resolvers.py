"""Cascading external metadata resolvers for TMDb, TVMaze, and Wikipedia."""

import logging
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

import httpx

from backend.config.models import EnrichedProgramDTO, MetadataProviderConfig
from backend.core.metadata_sanitizer import SanitizedTitleResult, MetadataSanitizer


class BaseMetadataResolver(ABC):
    """Abstract base class for external metadata provider resolvers."""

    @abstractmethod
    async def resolve(
        self, sanitized: SanitizedTitleResult, language: str = "en"
    ) -> Optional[EnrichedProgramDTO]:
        """Resolves metadata from external upstream API.

        Args:
            sanitized (SanitizedTitleResult): Sanitized programme title and parsed parameters.
            language (str): Target ISO language code.

        Returns:
            Optional[EnrichedProgramDTO]: Enriched metadata model if matched, None otherwise.
        """
        pass


class TMDbResolver(BaseMetadataResolver):
    """The Movie Database (TMDb) cinematic and TV series metadata resolver."""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self, api_key: str = "", client: Optional[httpx.AsyncClient] = None) -> None:
        """Initializes TMDb resolver with API key and optional HTTP client."""
        self.api_key = api_key.strip()
        self.client = client

    async def resolve(
        self, sanitized: SanitizedTitleResult, language: str = "en"
    ) -> Optional[EnrichedProgramDTO]:
        """Queries TMDb search/multi endpoint for movie or TV show matches."""
        if not self.api_key or not sanitized.cleaned_title:
            return None

        query_params: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": sanitized.cleaned_title,
            "language": language,
            "include_adult": "false",
        }
        if sanitized.release_year:
            query_params["year"] = sanitized.release_year

        url = f"{self.BASE_URL}/search/multi"
        try:
            if self.client:
                resp = await self.client.get(url, params=query_params, timeout=5.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=query_params, timeout=5.0)

            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            match = results[0]
            for candidate in results:
                title = candidate.get("title") or candidate.get("name") or ""
                if MetadataSanitizer.calculate_similarity(title, sanitized.cleaned_title) >= 0.70:
                    match = candidate
                    break

            media_type = match.get("media_type", "movie")
            title = match.get("title") or match.get("name") or sanitized.cleaned_title
            original_title = match.get("original_title") or match.get("original_name") or ""

            release_date = match.get("release_date") or match.get("first_air_date") or ""
            year = sanitized.release_year
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                except ValueError:
                    pass

            poster_path = match.get("poster_path")
            backdrop_path = match.get("backdrop_path")
            poster_url = f"{self.IMAGE_BASE_URL}/w780{poster_path}" if poster_path else ""
            backdrop_url = f"{self.IMAGE_BASE_URL}/w1280{backdrop_path}" if backdrop_path else ""

            tmdb_id = match.get("id")
            external_url = f"https://www.themoviedb.org/{media_type}/{tmdb_id}" if tmdb_id else ""

            return EnrichedProgramDTO(
                title=title,
                original_title=original_title,
                release_year=year,
                overview=match.get("overview") or "",
                poster_url=poster_url,
                backdrop_url=backdrop_url,
                rating=float(match["vote_average"]) if match.get("vote_average") is not None else None,
                vote_count=int(match["vote_count"]) if match.get("vote_count") is not None else None,
                provider="tmdb",
                external_url=external_url,
                found=True,
            )
        except Exception as e:
            logging.debug(f"TMDb resolution error for '{sanitized.cleaned_title}': {e}")
            return None


class TVMazeResolver(BaseMetadataResolver):
    """TVMaze open TV schedule and series metadata resolver."""

    BASE_URL = "https://api.tvmaze.com"
    _HTML_TAGS = re.compile(r"<[^>]+>")

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        """Initializes TVMaze resolver with optional HTTP client."""
        self.client = client

    async def resolve(
        self, sanitized: SanitizedTitleResult, language: str = "en"
    ) -> Optional[EnrichedProgramDTO]:
        """Queries TVMaze singlesearch endpoint."""
        if not sanitized.cleaned_title:
            return None

        query_params = {"q": sanitized.cleaned_title}
        url = f"{self.BASE_URL}/singlesearch/shows"

        try:
            if self.client:
                resp = await self.client.get(url, params=query_params, timeout=5.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=query_params, timeout=5.0)

            if resp.status_code != 200:
                return None

            data = resp.json()
            title = data.get("name") or sanitized.cleaned_title
            if MetadataSanitizer.calculate_similarity(title, sanitized.cleaned_title) < 0.60:
                return None

            premiered = data.get("premiered") or ""
            year = sanitized.release_year
            if premiered and len(premiered) >= 4:
                try:
                    year = int(premiered[:4])
                except ValueError:
                    pass

            raw_summary = data.get("summary") or ""
            cleaned_summary = self._HTML_TAGS.sub("", raw_summary).strip()

            images = data.get("image") or {}
            poster_url = images.get("original") or images.get("medium") or ""

            rating_obj = data.get("rating") or {}
            rating = float(rating_obj["average"]) if rating_obj.get("average") is not None else None

            return EnrichedProgramDTO(
                title=title,
                original_title=title,
                release_year=year,
                overview=cleaned_summary,
                poster_url=poster_url,
                rating=rating,
                genres=data.get("genres") or [],
                provider="tvmaze",
                external_url=data.get("url") or "",
                found=True,
            )
        except Exception as e:
            logging.debug(f"TVMaze resolution error for '{sanitized.cleaned_title}': {e}")
            return None


class WikipediaResolver(BaseMetadataResolver):
    """Wikipedia REST API resolver for general knowledge, talk shows, news, and sports."""

    BASE_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    HEADERS = {"User-Agent": "Pluvira/1.0 (https://pluvira.com; contact@pluvira.com)"}

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        """Initializes Wikipedia resolver with optional HTTP client."""
        self.client = client

    async def resolve(
        self, sanitized: SanitizedTitleResult, language: str = "en"
    ) -> Optional[EnrichedProgramDTO]:
        """Queries Wikipedia page summary endpoint."""
        if not sanitized.cleaned_title:
            return None

        lang = language.strip().lower() if language else "en"
        encoded_title = urllib.parse.quote(sanitized.cleaned_title.replace(" ", "_"))
        url = self.BASE_URL.format(lang=lang, title=encoded_title)

        try:
            if self.client:
                resp = await self.client.get(url, headers=self.HEADERS, timeout=5.0)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=self.HEADERS, timeout=5.0)

            if resp.status_code != 200:
                return None

            data = resp.json()
            if data.get("type") == "disambiguation":
                return None

            title = data.get("title") or sanitized.cleaned_title
            if MetadataSanitizer.calculate_similarity(title, sanitized.cleaned_title) < 0.60:
                return None

            thumbnail = data.get("thumbnail") or {}
            original_image = data.get("originalimage") or {}
            poster_url = original_image.get("source") or thumbnail.get("source") or ""

            content_urls = data.get("content_urls") or {}
            desktop_urls = content_urls.get("desktop") or {}
            external_url = desktop_urls.get("page") or ""

            return EnrichedProgramDTO(
                title=title,
                original_title=title,
                release_year=sanitized.release_year,
                overview=data.get("extract") or "",
                poster_url=poster_url,
                provider="wikipedia",
                external_url=external_url,
                found=True,
            )
        except Exception as e:
            logging.debug(f"Wikipedia resolution error for '{sanitized.cleaned_title}': {e}")
            return None


class CascadingMetadataResolver:
    """Cascading orchestrator querying TMDb, TVMaze, and Wikipedia in prioritized sequence."""

    def __init__(
        self,
        config: Optional[MetadataProviderConfig] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Initializes cascading resolver chain with provider configurations."""
        self.config = config or MetadataProviderConfig()
        self.client = client
        self._tmdb = TMDbResolver(api_key=self.config.tmdb_api_key or "", client=self.client)
        self._tvmaze = TVMazeResolver(client=self.client)
        self._wikipedia = WikipediaResolver(client=self.client)

    async def resolve(
        self, raw_title: str, language: str = "en"
    ) -> EnrichedProgramDTO:
        """Executes title sanitization and cascading upstream lookup across configured providers.

        Args:
            raw_title (str): Raw broadcast title.
            language (str): Target language code.

        Returns:
            EnrichedProgramDTO: Enriched metadata model. If no provider matched, returns found=False.
        """
        sanitized = MetadataSanitizer.sanitize(raw_title)
        if not sanitized.cleaned_title:
            return EnrichedProgramDTO(title=raw_title, found=False)

        if self.config.tmdb_api_key:
            res_tmdb = await self._tmdb.resolve(sanitized, language=language)
            if res_tmdb and res_tmdb.found:
                return res_tmdb

        if self.config.enable_tvmaze:
            res_tvmaze = await self._tvmaze.resolve(sanitized, language=language)
            if res_tvmaze and res_tvmaze.found:
                return res_tvmaze

        if self.config.enable_wikipedia:
            res_wiki = await self._wikipedia.resolve(sanitized, language=language)
            if res_wiki and res_wiki.found:
                return res_wiki

        return EnrichedProgramDTO(
            title=sanitized.cleaned_title,
            release_year=sanitized.release_year,
            found=False,
        )
