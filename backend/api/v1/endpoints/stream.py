"""Stream proxy REST API v1 endpoints."""

from typing import Optional
from fastapi import APIRouter, Query, status, Response, Depends, Request

from backend.services.stream_service import StreamService

router = APIRouter()


def get_stream_service() -> StreamService:
    """Dependency provider for StreamService instance."""
    return StreamService()


@router.options("/proxy", status_code=status.HTTP_200_OK)
async def proxy_stream_options() -> Response:
    """Handles CORS preflight OPTIONS requests for stream proxy.

    Returns:
        Response: Empty response with permissive CORS headers.
    """
    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        },
    )


@router.get("/proxy", status_code=status.HTTP_200_OK)
async def proxy_stream(
    request: Request,
    url: str = Query(..., description="Target stream URL to proxy"),
    user_agent: Optional[str] = Query(None, description="Optional custom User-Agent override"),
    service: StreamService = Depends(get_stream_service),
) -> Response:
    """Proxies an external stream URL and injects permissive CORS headers.

    Args:
        url (str): Target HTTP/HTTPS stream URL.
        user_agent (Optional[str]): Optional custom User-Agent header string.
        service (StreamService): StreamService dependency instance.

    Returns:
        StreamingResponse: Streamed content response with CORS headers.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await service.proxy_stream(target_url=url, custom_user_agent=user_agent, client_ip=client_ip)
