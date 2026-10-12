"""Export service layer encapsulating business logic for M3U playlist and XMLTV guide generation."""

from typing import Set, Optional
from fastapi import Response

from backend.core.exceptions import AuthenticationError
from backend.core.processor import DataProcessor
from backend.core.license_thresholds import (
    LicenseThresholdManager,
    FREE_TIER_MAX_CURATED_CHANNELS,
)
from backend.core.exporter import Exporter


class ExportService:
    """Service handling dynamic M3U playlist and XMLTV guide string generation and response formatting."""

    def __init__(self, processor: Optional[DataProcessor] = None) -> None:
        """Initializes export service with data processor instance.

        Args:
            processor (Optional[DataProcessor]): Override data processor instance.
        """
        self.processor = processor or DataProcessor()

    def export_m3u(self, playlist_id: Optional[str] = None, token: Optional[str] = None) -> Response:
        """Generates and serves processed M3U playlist file on-the-fly.

        Args:
            playlist_id (Optional[str]): Optional curated personal playlist ID/slug.
            token (Optional[str]): Optional export authentication token.

        Returns:
            Response: Stream attachment response with application/x-mpegurl media type.
        """
        if playlist_id:
            from backend.services.playlist_service import PlaylistService
            from backend.services.personal_channel_service import PersonalChannelService

            pl_service = PlaylistService()
            playlist = pl_service.get_playlist_by_id(playlist_id)

            if playlist.get("export_token") and playlist["export_token"] != token:
                raise AuthenticationError("Invalid or missing export token for playlist.")

            pch_service = PersonalChannelService()
            personal_channels = pch_service.get_channels(playlist_id)
            if not LicenseThresholdManager.is_pro_active():
                personal_channels = personal_channels[:FREE_TIER_MAX_CURATED_CHANNELS]

            export_channels = []
            for ch in personal_channels:
                slots = ch.get("slots", [])
                active_slots = [s for s in slots if not s.get("quarantined_at")]
                if active_slots:
                    primary = active_slots[0]
                    export_channels.append({
                        "name": ch.get("name", "Unknown"),
                        "url": primary.get("url", ""),
                        "group": ch.get("group", ""),
                        "logo": ch.get("logo", ""),
                        "user_agent": primary.get("user_agent"),
                        "is_included": True,
                    })

            content = Exporter.generate_m3u(export_channels)
            filename = f"pluvira_{playlist_id}.m3u"
        else:
            channels = self.processor.get_processed_channels()
            content = Exporter.generate_m3u(channels)
            filename = "pluvira.m3u"

        return Response(
            content=content,
            media_type="application/x-mpegurl",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def export_xmltv(self) -> Response:
        """Generates and serves processed XMLTV guide file response.

        Returns:
            Response: Stream attachment response with application/xml media type.
        """
        channels = self.processor.get_processed_channels()

        mapped_ids: Set[str] = {
            ch["epg_id"]
            for ch in channels
            if ch.get("is_included", True) and ch.get("is_mapped") and ch.get("epg_id")
        }

        epg_data = self.processor.get_epg_data(mapped_ids) if mapped_ids else {}

        content = Exporter.generate_xmltv(channels, epg_data)
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="pluvira_epg.xml"'},
        )
