"""Dynamic M3U playlist and XMLTV guide export REST endpoints."""

from typing import Optional
from fastapi import APIRouter, Response, status, Query, Depends
from backend.services.export_service import ExportService

router = APIRouter()


def get_export_service() -> ExportService:
    """Dependency provider for ExportService instance."""
    return ExportService()


@router.get("/m3u", status_code=status.HTTP_200_OK)
def export_m3u_playlist(
    list: Optional[str] = Query(None, description="Optional curated personal playlist identifier or slug"),
    token: Optional[str] = Query(None, description="Optional secret export token for custom playlist"),
    service: ExportService = Depends(get_export_service),
) -> Response:
    """Generates and serves processed M3U playlist file on-the-fly.

    Returns:
        Response: Stream attachment response with application/x-mpegurl media type.
    """
    return service.export_m3u(playlist_id=list, token=token)


@router.get("/xml", status_code=status.HTTP_200_OK)
def export_xmltv_guide(service: ExportService = Depends(get_export_service)) -> Response:
    """Generates and serves processed XMLTV guide file on-the-fly using DataProcessor cache.

    Returns:
        Response: Stream attachment response with application/xml media type.
    """
    return service.export_xmltv()
