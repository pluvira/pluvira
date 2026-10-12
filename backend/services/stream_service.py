"""Stream service layer encapsulating CORS proxy streaming logic."""

import logging
from typing import AsyncGenerator, Optional
import httpx
from fastapi import Response
from fastapi.responses import StreamingResponse

from backend.core.exceptions import ValidationDomainError, BadGatewayError

from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.utils import StreamUtils


class StreamService:
    """Service handling stream proxying and CORS header injection for video playback."""

    def __init__(self, config_handler: Optional[YAMLConfigHandler] = None) -> None:
        """Initializes stream service with configuration handler.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()

    async def proxy_stream(
        self,
        target_url: str,
        custom_user_agent: Optional[str] = None,
        client_ip: str = "127.0.0.1",
    ) -> Response:
        """Proxies an HTTP stream URL, streaming chunks and injecting CORS headers.

        Args:
            target_url (str): Remote stream URL to fetch.
            custom_user_agent (Optional[str]): Explicit User-Agent override.

        Returns:
            StreamingResponse: Streaming HTTP response with CORS headers.

        Raises:
            HTTPException: 400 Bad Request if URL scheme is unsupported or invalid.
            HTTPException: 502 Bad Gateway if upstream connection fails.
        """
        if not target_url.startswith(("http://", "https://")):
            raise ValidationDomainError("Invalid URL scheme. Only HTTP and HTTPS streams are supported.")

        from backend.core.license_thresholds import LicenseThresholdManager
        LicenseThresholdManager.acquire_stream_lease(client_ip)

        try:
            config = self.config_handler.load_config()
            global_ua = config.settings.user_agent or "Mozilla/5.0"
        except Exception:
            global_ua = "Mozilla/5.0"

        ua = StreamUtils.resolve_user_agent(custom_user_agent or "", "", global_ua)
        req_headers = {
            "User-Agent": ua,
            "Accept": "*/*",
        }

        try:
            client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False)
            req = client.build_request("GET", target_url, headers=req_headers)
            response = await client.send(req, stream=True)
            response.raise_for_status()

            async def content_generator() -> AsyncGenerator[bytes, None]:
                try:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            media_type = response.headers.get("content-type", "application/octet-stream")
            final_url_str = str(response.url)
            clean_media_type = media_type.lower()

            is_m3u8 = (
                "mpegurl" in clean_media_type
                or "m3u" in clean_media_type
                or final_url_str.split("?")[0].endswith((".m3u8", ".m3u"))
            )

            cors_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Cache-Control": response.headers.get("cache-control", "no-cache"),
            }

            if is_m3u8:
                try:
                    chunks = []
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        chunks.append(chunk)
                    raw_content = b"".join(chunks)
                    manifest_text = raw_content.decode("utf-8", errors="replace")

                    rewritten_manifest = StreamUtils.rewrite_m3u8_manifest(
                        manifest_text=manifest_text,
                        base_url=final_url_str,
                        custom_user_agent=ua,
                    )
                    return Response(
                        content=rewritten_manifest,
                        status_code=response.status_code,
                        media_type="application/x-mpegurl",
                        headers=cors_headers,
                    )
                finally:
                    await response.aclose()
                    await client.aclose()

            return StreamingResponse(
                content_generator(),
                status_code=response.status_code,
                media_type=media_type,
                headers=cors_headers,
            )

        except httpx.HTTPStatusError as hse:
            logging.error(f"Stream proxy HTTP error for '{target_url}': {hse}")
            raise BadGatewayError(f"Upstream stream server returned HTTP {hse.response.status_code}.")
        except Exception as e:
            logging.error(f"Stream proxy connection failure for '{target_url}': {e}")
            raise BadGatewayError(f"Failed to connect to upstream stream server: {e}")
