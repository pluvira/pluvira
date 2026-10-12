"""Rich EPG metadata enrichment and artwork proxy REST API endpoints."""

import mimetypes
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, status, Depends, Response
from fastapi.responses import FileResponse
from backend.core.exceptions import EntityNotFoundError

from backend.config.models import (
    EnrichedProgramDTO,
    MetadataEnrichPayload,
    MetadataBulkEnrichPayload,
    MetadataSearchPayload,
    StreamProbePayload,
)
from backend.api.deps import get_current_user
from backend.services.metadata_service import MetadataService


router = APIRouter()


def get_metadata_service() -> MetadataService:
    """Dependency provider for MetadataService instance."""
    return MetadataService()


@router.get("/artwork/{image_type}/{image_hash}", status_code=status.HTTP_200_OK)
async def get_artwork_image(
    image_type: str,
    image_hash: str,
    service: MetadataService = Depends(get_metadata_service),
) -> Response:
    """Serves cached artwork image from RAM disk proxy without authentication.

    Args:
        image_type (str): 'poster' or 'backdrop'.
        image_hash (str): Hash filename of cached artwork.
        service (MetadataService): MetadataService dependency.

    Returns:
        FileResponse: Cached image file stream.

    Raises:
        HTTPException: 404 if artwork file is not found.
    """
    path = service.get_artwork_path(image_hash)
    if not path or not path.exists():
        raise EntityNotFoundError(f"Artwork '{image_hash}' not found in cache")

    media_type, _ = mimetypes.guess_type(str(path))

    return FileResponse(
        path=path,
        media_type=media_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post(
    "/enrich",
    status_code=status.HTTP_200_OK,
    response_model=EnrichedProgramDTO,
    dependencies=[Depends(get_current_user)],
)
async def enrich_program(
    payload: MetadataEnrichPayload,
    service: MetadataService = Depends(get_metadata_service),
) -> EnrichedProgramDTO:
    """Enriches a single programme title with external metadata, synopsis, ratings, and artwork.

    Args:
        payload (MetadataEnrichPayload): Request parameters.
        service (MetadataService): MetadataService dependency.

    Returns:
        EnrichedProgramDTO: Enriched metadata object.
    """
    return await service.enrich_program(
        title=payload.title,
        release_year=payload.release_year,
        language=payload.language,
        force_refresh=payload.force_refresh,
    )


@router.post(
    "/bulk-enrich",
    status_code=status.HTTP_200_OK,
    response_model=List[EnrichedProgramDTO],
    dependencies=[Depends(get_current_user)],
)
async def bulk_enrich_programs(
    payload: MetadataBulkEnrichPayload,
    service: MetadataService = Depends(get_metadata_service),
) -> List[EnrichedProgramDTO]:
    """Enriches multiple programme titles in batch.

    Args:
        payload (MetadataBulkEnrichPayload): Request parameters.
        service (MetadataService): MetadataService dependency.

    Returns:
        List[EnrichedProgramDTO]: List of enriched metadata objects.
    """
    return await service.bulk_enrich(
        titles=payload.titles,
        language=payload.language,
    )


@router.post(
    "/search",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)],
)
async def search_metadata(
    payload: MetadataSearchPayload,
    service: MetadataService = Depends(get_metadata_service),
) -> Dict[str, Any]:
    """Searches programme metadata using Pro sub-5ms fuzzy search or SQLite fallback.

    Args:
        payload (MetadataSearchPayload): Search parameters.
        service (MetadataService): MetadataService dependency.

    Returns:
        Dict[str, Any]: Search results payload.
    """
    return await service.search_epg(
        query=payload.query,
        genre=payload.genre,
        min_rating=payload.min_rating,
        limit=payload.limit,
    )


@router.post(
    "/probe",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)],
)
async def probe_stream(
    payload: StreamProbePayload,
    service: MetadataService = Depends(get_metadata_service),
) -> Dict[str, Any]:
    """Executes byte-range stream probe using Pro native engine or Core fallback.

    Args:
        payload (StreamProbePayload): Stream probe parameters.
        service (MetadataService): MetadataService dependency.

    Returns:
        Dict[str, Any]: Stream probe metrics.
    """
    return await service.probe_stream(
        stream_url=payload.stream_url,
        timeout_ms=payload.timeout_ms,
    )
