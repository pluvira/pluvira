"""BSL 1.1 Free Tier resource constraints and stream lease concurrency manager."""

import time
import threading
from typing import Dict, List, Optional
from backend.core.exceptions import (
    MaxSourcesExceededError,
    MaxChannelsExceededError,
    MaxConcurrentStreamsExceededError,
    MaxPlaylistsExceededError,
    PersonalChannelLimitExceeded,
    MaxSlotsExceededError,
    LicenseThresholdExceededError,
)
from backend.core.pro_bridge import ProBridge

FREE_TIER_MAX_ACTIVE_SOURCES: int = 2
FREE_TIER_MAX_CHANNELS: int = 2500
FREE_TIER_MAX_CURATED_CHANNELS: int = 25
FREE_TIER_MAX_SLOTS: int = 2
PRO_MAX_SLOTS: int = 7
FREE_TIER_MAX_CONCURRENT_STREAMS: int = 2
FREE_TIER_MAX_PLAYLISTS: int = 1
STREAM_LEASE_TIMEOUT_SECONDS: int = 60


class LicenseThresholdManager:
    """Enforces BSL 1.1 resource limits when running in Free Tier."""

    _lock = threading.RLock()
    _stream_leases: Dict[str, float] = {}

    @classmethod
    def is_pro_active(cls) -> bool:
        """Checks if Pluvira Pro is active with a valid license."""
        return ProBridge.is_available()

    @classmethod
    def has_module(cls, module_slug: str) -> bool:
        """Checks whether a specific Pro module entitlement is active.

        Args:
            module_slug (str): Feature module identifier (e.g. 'auto_merge', 'cascade_rewrite').

        Returns:
            bool: True if module is present in active license claims, False otherwise.
        """
        if not cls.is_pro_active():
            return False
        info = ProBridge.get_edition_info()
        lic = info.get("license") or {}
        modules = lic.get("modules") or []
        target = module_slug.lower().replace("-", "_")
        normalized = {str(m).lower().replace("-", "_") for m in modules}
        return target in normalized

    @classmethod
    def get_max_concurrent_streams(cls) -> int:
        """Resolves dynamic maximum concurrent stream views quota based on active license or free tier."""
        if not cls.is_pro_active():
            return FREE_TIER_MAX_CONCURRENT_STREAMS
        info = ProBridge.get_edition_info()
        lic = info.get("license") or {}
        max_ips = lic.get("max_ips") or lic.get("ips")
        if max_ips and isinstance(max_ips, int) and max_ips > 0:
            return max_ips
        return 20

    @classmethod
    def validate_active_sources(cls, active_sources_count: int) -> None:
        """Validates that active M3U playlist sources do not exceed Free Tier threshold.

        Args:
            active_sources_count (int): Number of enabled M3U sources.

        Raises:
            MaxSourcesExceededError: If active sources exceed limit and Pro is inactive.
        """
        if cls.is_pro_active():
            return
        if active_sources_count > FREE_TIER_MAX_ACTIVE_SOURCES:
            raise MaxSourcesExceededError(
                f"Free tier limit exceeded: maximum {FREE_TIER_MAX_ACTIVE_SOURCES} active M3U playlists allowed. Found {active_sources_count}."
            )

    @classmethod
    def validate_channel_count(cls, channel_count: int) -> None:
        """Validates that total channels do not exceed Free Tier threshold.

        Args:
            channel_count (int): Number of channels processed.

        Raises:
            MaxChannelsExceededError: If total channels exceed limit and Pro is inactive.
        """
        if cls.is_pro_active():
            return
        if channel_count > FREE_TIER_MAX_CHANNELS:
            raise MaxChannelsExceededError(
                f"Free tier limit exceeded: maximum {FREE_TIER_MAX_CHANNELS} total channels allowed. Found {channel_count}."
            )

    @classmethod
    def get_max_slots(cls) -> int:
        """Returns maximum permitted failover slots based on Pro license status."""
        if not cls.is_pro_active():
            return FREE_TIER_MAX_SLOTS
        info = ProBridge.get_edition_info()
        lic = info.get("license") or {}
        custom_slots = lic.get("max_slots")
        if custom_slots and isinstance(custom_slots, int) and custom_slots > 0:
            return custom_slots
        return PRO_MAX_SLOTS

    @classmethod
    def validate_auto_map_epg(
        cls,
        scope: str = "curated",
        similarity_threshold: float = 0.85,
        channel_count: int = 0,
    ) -> None:
        """Validates that auto-assign EPG request conforms to active tier limits.

        Args:
            scope (str): Target scope ('curated' or 'all').
            similarity_threshold (float): Minimum matching threshold.
            channel_count (int): Number of channels to evaluate.

        Raises:
            LicenseThresholdExceededError: If Free Tier attempts global scope or deep fuzzy < 0.85 or > 25 channels.
        """
        if cls.is_pro_active():
            return

        if scope.lower() != "curated":
            raise LicenseThresholdExceededError(
                "Catalog-wide auto-assign requires Pluvira Pro. Free tier is limited to curated channels in 'My List'."
            )

        if channel_count > FREE_TIER_MAX_CURATED_CHANNELS:
            raise LicenseThresholdExceededError(
                f"Free tier limit exceeded: maximum {FREE_TIER_MAX_CURATED_CHANNELS} channels in 'My List' can be auto-assigned."
            )

        if similarity_threshold < 0.85:
            raise LicenseThresholdExceededError(
                "Free tier similarity threshold cannot be lower than 0.85. Pro license required for deep fuzzy matching."
            )

    @classmethod
    def validate_curated_channel_count(cls, curated_channel_count: int) -> None:
        """Validates that personal curated channels do not exceed Free Tier threshold.

        Args:
            curated_channel_count (int): Number of curated channels in playlist.

        Raises:
            PersonalChannelLimitExceeded: If curated channels exceed limit and Pro is inactive.
        """
        if cls.is_pro_active():
            return
        if curated_channel_count > FREE_TIER_MAX_CURATED_CHANNELS:
            raise PersonalChannelLimitExceeded(
                f"Free tier limit exceeded: maximum {FREE_TIER_MAX_CURATED_CHANNELS} channels allowed in My List. Found {curated_channel_count}."
            )

    @classmethod
    def validate_slot_count(cls, current_slot_count: int) -> None:
        """Validates that candidate stream slots do not exceed tier threshold.

        Args:
            current_slot_count (int): Current number of stream slots on channel.

        Raises:
            MaxSlotsExceededError: If slot count exceeds limit for active tier.
        """
        max_slots = cls.get_max_slots()
        if current_slot_count > max_slots:
            raise MaxSlotsExceededError(
                f"Limit exceeded: maximum {max_slots} stream slots allowed ({'Pro' if cls.is_pro_active() else 'Free'} Tier)."
            )

    @classmethod
    def validate_playlist_count(cls, playlist_count: int) -> None:
        """Validates that personal playlist count does not exceed Free Tier threshold.

        Args:
            playlist_count (int): Number of created personal playlists.

        Raises:
            MaxPlaylistsExceededError: If personal playlists exceed limit and Pro is inactive.
        """
        if cls.is_pro_active():
            return
        if playlist_count > FREE_TIER_MAX_PLAYLISTS:
            raise MaxPlaylistsExceededError(
                f"Free tier limit exceeded: maximum {FREE_TIER_MAX_PLAYLISTS} personal playlist allowed. Found {playlist_count}."
            )

    @classmethod
    def acquire_stream_lease(cls, client_ip: str) -> None:
        """Acquires a volatile streaming lease for client IP address enforcing tier quota.

        Args:
            client_ip (str): Client IP address.

        Raises:
            MaxConcurrentStreamsExceededError: If active unique streaming IPs exceed limit.
        """
        max_allowed = cls.get_max_concurrent_streams()
        with cls._lock:
            now = time.time()
            cls._clean_stale_leases(now)

            if client_ip in cls._stream_leases:
                cls._stream_leases[client_ip] = now
                return

            if len(cls._stream_leases) >= max_allowed:
                tier_label = "Pro" if cls.is_pro_active() else "Free"
                raise MaxConcurrentStreamsExceededError(
                    f"{tier_label} tier limit exceeded: maximum {max_allowed} concurrent stream views active."
                )

            cls._stream_leases[client_ip] = now

    @classmethod
    def release_stream_lease(cls, client_ip: str) -> None:
        """Releases a streaming lease for client IP address."""
        with cls._lock:
            cls._stream_leases.pop(client_ip, None)

    @classmethod
    def get_active_stream_leases(cls) -> List[str]:
        """Returns list of currently active client IP stream leases."""
        with cls._lock:
            cls._clean_stale_leases(time.time())
            return list(cls._stream_leases.keys())

    @classmethod
    def reset_stream_leases(cls) -> None:
        """Clears all active stream leases."""
        with cls._lock:
            cls._stream_leases.clear()

    @classmethod
    def _clean_stale_leases(cls, current_time: float) -> None:
        """Removes expired stream leases older than lease timeout."""
        stale_ips = [
            ip for ip, last_seen in cls._stream_leases.items()
            if (current_time - last_seen) > STREAM_LEASE_TIMEOUT_SECONDS
        ]
        for ip in stale_ips:
            del cls._stream_leases[ip]
