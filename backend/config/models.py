"""Consolidated Pydantic schemas for data validation and configuration."""

import re
import secrets
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class FilePermissions(BaseModel):
    """Model representing Unix file permissions."""

    mode: str = Field(default="0644", description="Octal representation of file mode")
    owner: str = Field(default="", description="File owner username")
    group: str = Field(default="", description="File group name")

    @field_validator("mode")
    @classmethod
    def validate_octal_mode(cls, value: str) -> str:
        """Validates octal file mode format.

        Args:
            value (str): Input file mode.

        Returns:
            str: Validated octal mode string.

        Raises:
            ValueError: If mode is not a valid 3-4 digit octal string.
        """
        if not re.match(r"^[0-7]{3,4}$", value):
            raise ValueError("File mode must be a valid octal representation (e.g., '0644')")
        return value


class Substitution(BaseModel):
    """Model representing a regex substitution rule (legacy support)."""

    pattern: str = Field(..., description="Regex pattern to search for")
    replacement: str = Field(..., description="Replacement string")
    description: Optional[str] = Field(default=None)


class RewriteRule(BaseModel):
    """Model representing a metadata rewrite rule."""

    field: str = Field(..., description="Field to target: name, group, logo, url, user_agent, or force_proxy")
    pattern: str = Field(default="", description="Search pattern")
    replacement: str = Field(..., description="Replacement string or absolute value")
    mode: str = Field(default="regex", description="Pattern matching mode: regex, wildcard, text, or replace")
    enabled: bool = Field(default=True)
    description: Optional[str] = Field(default=None)


class FilterRule(BaseModel):
    """Model representing a single channel filter rule."""

    field: str = Field(..., description="M3U attribute field (e.g., group-title)")
    regex: str = Field(..., description="Regex pattern to match")


class Filters(BaseModel):
    """Model containing allow and deny filter rules lists."""

    allow: List[FilterRule] = Field(default_factory=list)
    deny: List[FilterRule] = Field(default_factory=list)


class LinkTestSettings(BaseModel):
    """Settings for the anti-ban polite link scanner."""

    min_delay: float = Field(default=1.5, ge=0)
    max_delay: float = Field(default=3.5, ge=0)


class MdnsConfig(BaseModel):
    """Configuration for local mDNS (Zeroconf) network discovery."""

    enabled: bool = Field(default=True, description="Enable mDNS LAN service broadcast")
    service_type: str = Field(
        default="_pluvira._tcp.local.",
        description="mDNS service registration type",
    )


class CastMemberDTO(BaseModel):
    """Cast member model for enriched metadata."""

    name: str = Field(..., description="Actor or performer name")
    character: Optional[str] = Field(default="", description="Role or character name")
    photo_url: Optional[str] = Field(default="", description="Actor headshot photo URL")


class EnrichedProgramDTO(BaseModel):
    """Normalized and enriched program metadata model."""

    id: Optional[str] = Field(default=None, description="EPG program item ID or reference")
    hash_key: Optional[str] = Field(default=None, description="Deterministic SHA256 composite lookup hash")
    found: bool = Field(default=True, description="Whether enrichment data was resolved from upstream")
    provider: str = Field(default="", description="Upstream metadata provider (tmdb, tvmaze, wikipedia)")
    title: str = Field(..., description="Enriched title")
    original_title: Optional[str] = Field(default="", description="Original title from provider")
    overview: Optional[str] = Field(default="", description="Program synopsis or overview")
    poster_url: Optional[str] = Field(default="", description="Poster artwork URL or proxy endpoint")
    backdrop_url: Optional[str] = Field(default="", description="Backdrop / banner artwork URL or proxy endpoint")
    rating: Optional[float] = Field(default=None, ge=0.0, le=10.0, description="Community score (0-10)")
    vote_count: Optional[int] = Field(default=None, ge=0, description="Community vote count")
    release_year: Optional[int] = Field(default=None, description="Release or broadcast year")
    genres: List[str] = Field(default_factory=list, description="Genre tags")
    director: Optional[str] = Field(default="", description="Director name")
    cast: List[CastMemberDTO] = Field(default_factory=list, description="Cast members list")
    external_url: Optional[str] = Field(default="", description="External reference URL")


class MetadataProviderConfig(BaseModel):
    """Configuration for external rich metadata providers."""

    tmdb_api_key: Optional[str] = Field(default="", description="The Movie Database (TMDb) API key")
    tvdb_api_key: Optional[str] = Field(default="", description="TheTVDB API key")
    trakt_client_id: Optional[str] = Field(default="", description="Trakt.tv client ID")
    enable_tvmaze: bool = Field(default=True, description="Enable TVMaze fallback provider (free/open)")
    enable_wikipedia: bool = Field(default=True, description="Enable Wikipedia REST fallback provider (free/open)")
    metadata_retention_days: int = Field(default=30, ge=1, le=365, description="Cache retention TTL for movie metadata in days")


class MetadataEnrichPayload(BaseModel):
    """Payload for enriching programme title."""

    title: str = Field(..., min_length=1, description="Raw broadcast programme title")
    release_year: Optional[int] = Field(default=None, description="Optional release year")
    language: str = Field(default="en", description="Language code")
    force_refresh: bool = Field(default=False, description="Bypass cache and force upstream refresh")


class MetadataBulkEnrichPayload(BaseModel):
    """Payload for bulk programme enrichment."""

    titles: List[str] = Field(..., min_length=1, description="List of programme titles")
    language: str = Field(default="en", description="Language code")


class MetadataSearchPayload(BaseModel):
    """Payload for fast metadata schedule search."""

    query: str = Field(..., min_length=1, description="Search query")
    genre: Optional[str] = Field(default=None, description="Optional genre filter")
    min_rating: Optional[float] = Field(default=None, ge=0.0, le=10.0, description="Minimum rating filter")
    limit: int = Field(default=50, ge=1, le=200, description="Max results")


class StreamProbePayload(BaseModel):
    """Payload for live stream byte-range probing."""

    stream_url: str = Field(..., min_length=1, description="Stream URL to probe")
    timeout_ms: int = Field(default=3000, ge=500, le=10000, description="Probe timeout in ms")


class BulkSourceStatusPayload(BaseModel):
    """Payload for bulk source status modification."""

    names: List[str] = Field(..., description="List of source names")
    action: str = Field(..., description="Action to perform: 'enable', 'disable', 'toggle'")


class BulkSourceDeletePayload(BaseModel):
    """Payload for bulk source deletion."""

    names: List[str] = Field(..., description="List of source names to delete")


class BulkSourceUserAgentPayload(BaseModel):
    """Payload for bulk source User-Agent update."""

    names: List[str] = Field(..., description="List of source names")
    user_agent: str = Field(default="", description="New User-Agent string to set or empty to reset")


class BulkSourceReorderPayload(BaseModel):
    """Payload for bulk source sequential reordering."""

    names: List[str] = Field(..., description="Ordered list of source names")


class BulkSourceRefreshPayload(BaseModel):
    """Payload for bulk source refresh."""

    names: List[str] = Field(..., description="List of source names to refresh")


class NotificationEventConfig(BaseModel):
    """Configuration for individual event triggers."""

    @classmethod
    def get_default_dict(cls) -> Dict[str, Any]:
        """Returns a dictionary containing all event triggers with their default fallback values.

        Returns:
            Dict[str, Any]: Default event toggles map.
        """
        return cls().model_dump()

    update_success: bool = Field(default=True)
    update_failure: bool = Field(default=True)
    link_test_report: bool = Field(default=True)
    link_ko_detected: bool = Field(default=True)
    disk_space_warning: bool = Field(default=True)
    source_download_failure: bool = Field(default=True)
    source_empty_malformed: bool = Field(default=True)
    partial_acquisition: bool = Field(default=True)
    massive_channel_drop: bool = Field(default=True)
    massive_drop_threshold_pct: float = Field(default=30.0, ge=1.0, le=90.0)
    link_recovered: bool = Field(default=True)
    source_unhealth_warning: bool = Field(default=True)
    source_health_threshold_pct: float = Field(default=70.0, ge=1.0, le=99.0)
    suspicious_redirect_detected: bool = Field(default=True)
    atomic_write_failure: bool = Field(default=True)
    orphan_lock_recovered: bool = Field(default=True)
    min_ram_disk_free_mb: float = Field(default=30.0, ge=5.0, le=500.0)
    unmapped_included_warning: bool = Field(default=True)
    unmapped_included_threshold_pct: float = Field(default=20.0, ge=1.0, le=95.0)
    epg_expiration_warning: bool = Field(default=True)
    min_epg_future_hours: float = Field(default=24.0, ge=1.0, le=168.0)
    rewrite_conflict_warning: bool = Field(default=True)
    config_save_failure: bool = Field(default=True)
    service_lifecycle_event: bool = Field(default=True)
    epg_source_unused: bool = Field(default=True)
    slow_processing_warning: bool = Field(default=True)
    slow_processing_threshold_s: float = Field(default=2.0, ge=0.5, le=30.0)
    scheduled_job_skipped: bool = Field(default=True)
    duplicate_channel_warning: bool = Field(default=True)
    m3u_parsing_error: bool = Field(default=True)
    xmltv_parsing_error: bool = Field(default=True)
    system_high_load: bool = Field(default=True)
    cpu_load_threshold_pct: float = Field(default=85.0, ge=10.0, le=99.0)
    temp_threshold_c: float = Field(default=75.0, ge=40.0, le=100.0)
    api_error_500: bool = Field(default=True)
    link_failover_triggered: bool = Field(default=True)


class NotificationSettings(BaseModel):
    """Configuration settings for system notifications."""

    enabled: bool = Field(default=False)
    urls: List[str] = Field(default_factory=list)
    events: NotificationEventConfig = Field(default_factory=NotificationEventConfig)


class SourceSettings(BaseModel):
    """Configuration settings defined globally or per-source."""

    output_m3u: Optional[str] = None
    output_epg: Optional[str] = None
    temp_dir: Optional[str] = None
    device_name: Optional[str] = Field(default="Pluvira", description="Human-readable server instance and mDNS broadcast name")
    mdns: Optional[MdnsConfig] = Field(default_factory=MdnsConfig, description="mDNS discovery settings")
    user_agent: Optional[str] = None
    epg_retention_days: Optional[int] = Field(default=None, ge=1, le=30)
    file_permissions: Optional[FilePermissions] = None
    substitutions: Optional[List[Substitution]] = Field(default=None, exclude=True)
    rewrites: Optional[List[RewriteRule]] = Field(
        default_factory=list,
        exclude=True,
        description="Metadata rewrite rules (persisted in SQLite metadata_rules table)",
    )
    filters: Optional[Filters] = Field(default=None, exclude=True)
    mapping_overrides: Optional[Dict[str, str]] = Field(default=None, exclude=True)
    notification_urls: Optional[List[str]] = Field(default=None, exclude=True)
    notifications: Optional[NotificationSettings] = Field(default_factory=NotificationSettings, exclude=True)
    allow_channels: Optional[List[str]] = Field(default_factory=list, exclude=True)
    deny_channels: Optional[List[str]] = Field(default_factory=list, exclude=True)
    link_test_settings: Optional[LinkTestSettings] = None
    search_debounce_ms: Optional[int] = Field(default=300, ge=0, le=2000)
    force_proxy: Optional[bool] = Field(default=False)
    stream_auto_purge: Optional[bool] = Field(default=True)
    purge_days_threshold: Optional[int] = Field(default=7, ge=1, le=90)
    onboarding_completed: Optional[bool] = Field(default=False)
    metadata_providers: Optional[MetadataProviderConfig] = Field(default_factory=MetadataProviderConfig)

    @model_validator(mode="after")
    def sync_notification_urls(self) -> "SourceSettings":
        """Synchronizes notification_urls and notifications.urls lists.

        Returns:
            SourceSettings: Self instance.
        """
        if self.notification_urls and self.notifications:
            if not self.notifications.urls:
                self.notifications.urls = list(self.notification_urls)
        elif self.notifications and self.notifications.urls:
            if self.notification_urls is None:
                self.notification_urls = list(self.notifications.urls)
        return self


class EPGSource(BaseModel):
    """Model representing a global XMLTV guide source."""

    name: str = Field(..., description="Unique name of the EPG guide source")
    enabled: bool = Field(default=True, description="Enable or disable this EPG source")
    url: str = Field(..., description="URL or local path of the XMLTV guide")
    user_agent: Optional[str] = Field(default=None, description="Custom User-Agent header")
    sort_order: int = Field(default=0, description="Sequential priority sort order")


class Source(BaseModel):
    """Model representing an IPTV M3U source configuration."""

    name: str = Field(..., description="Unique name of the source")
    enabled: bool = Field(default=True, description="Enable or disable this source")
    m3u_url: str = Field(..., description="URL or local path of the M3U")
    settings: Optional[SourceSettings] = None
    sort_order: int = Field(default=0, description="Sequential priority sort order")


class StreamRef(BaseModel):
    """Reference to a stream URL belonging to a specific source."""

    url: str = Field(..., description="Stream endpoint URL")
    source: str = Field(..., description="Name of the IPTV source provider")
    user_agent: Optional[str] = Field(default=None, description="Optional explicit User-Agent override")


class ChannelMerge(BaseModel):
    """Configuration model for a merged Master channel with primary and backup streams."""

    name: Optional[str] = Field(default=None)
    epg_id: Optional[str] = Field(default=None)
    logo: Optional[str] = Field(default=None)
    group: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    primary_stream: StreamRef = Field(...)
    backup_streams: List[StreamRef] = Field(default_factory=list)


class PersonalPlaylist(BaseModel):
    """Configuration model for a Curated Personal Playlist."""

    id: str = Field(..., description="Unique playlist identifier or slug")
    name: str = Field(..., description="User-facing playlist display name")
    export_token: str = Field(default="", description="Secret security token for authenticated M3U exports")
    is_default: bool = Field(default=False, description="Whether this is the primary default playlist")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")


class ChannelSlot(BaseModel):
    """Model representing a physical stream slot bound to a PersonalChannel (Slot-Cap 0-6)."""

    id: Optional[str] = Field(default=None, description="Unique slot identifier")
    personal_channel_id: str = Field(..., description="Target PersonalChannel identifier")
    slot_index: int = Field(default=0, ge=0, le=6, description="Slot position (0=Primary, 1-6=Backups)")
    url: str = Field(..., description="Physical stream endpoint URL")
    source: str = Field(..., description="IPTV source provider name")
    user_agent: Optional[str] = Field(default=None, description="Custom User-Agent override")
    health_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Computed stream health score (0-100)")
    is_locked: bool = Field(default=False, description="Manual lock flag preventing auto-attach override")
    consecutive_errors: int = Field(default=0, ge=0, description="Consecutive network/decode error count")
    quarantined_at: Optional[str] = Field(default=None, description="Timestamp when stream entered quarantine")


class ChannelSuggestion(BaseModel):
    """Model representing a candidate stream pending user approval (Confidence 70-89%)."""

    id: Optional[str] = Field(default=None, description="Unique suggestion identifier")
    personal_channel_id: str = Field(..., description="Target PersonalChannel identifier")
    url: str = Field(..., description="Candidate stream endpoint URL")
    source: str = Field(..., description="IPTV source provider name")
    user_agent: Optional[str] = Field(default=None, description="Custom User-Agent override")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Fuzzy/EPG match confidence score")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp when suggestion was added")


class PersonalChannel(BaseModel):
    """Logical Personal Channel entity containing up to 7 ordered stream slots."""

    id: str = Field(..., description="Unique personal channel identifier")
    playlist_id: str = Field(default="default", description="Parent PersonalPlaylist identifier")
    name: str = Field(..., description="User-facing channel display name")
    logo: Optional[str] = Field(default="", description="Channel logo URL")
    epg_id: Optional[str] = Field(default="", description="Namespaced EPG channel ID")
    group: Optional[str] = Field(default="", description="Category group name")
    custom_order: int = Field(default=0, ge=0, description="User custom display order index")
    is_pinned: bool = Field(default=False, description="Whether channel is pinned to top of grid")
    slots: List[ChannelSlot] = Field(default_factory=list, description="Ordered candidate stream slots (max 7)")
    suggestions: List[ChannelSuggestion] = Field(default_factory=list, description="Pending candidate stream suggestions")


class AuthConfig(BaseModel):
    """Configuration for backend JWT authentication."""

    enabled: bool = Field(default=False, description="Enable JWT authentication requirement")
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    token_expire_minutes: int = Field(default=1440, ge=1, description="Token expiration in minutes (default 24h)")
    username: str = Field(default="admin", description="Admin username")
    password: str = Field(default="admin", description="Admin password")


class GlobalConfig(BaseModel):
    """Root configuration model for config.yaml."""

    version: int = Field(default=1, ge=1, description="Configuration schema version")
    settings: SourceSettings = Field(..., description="Global default settings")
    auth: AuthConfig = Field(default_factory=AuthConfig, description="Authentication configuration")
    sources: List[Source] = Field(default_factory=list, exclude=True)
    epg_sources: List[EPGSource] = Field(default_factory=list, exclude=True)
    channel_merges: Optional[Dict[str, ChannelMerge]] = Field(default_factory=dict, exclude=True)
    individual_rewrites: Optional[Dict[str, List[RewriteRule]]] = Field(default_factory=dict, exclude=True)

    def get_event_config(self) -> NotificationEventConfig:
        """Safely retrieves NotificationEventConfig object with default fallback."""
        if self.settings and self.settings.notifications and self.settings.notifications.events:
            return self.settings.notifications.events
        return NotificationEventConfig()


class UpdateSourceProgress(BaseModel):
    """Progress status of an individual M3U or EPG source during acquisition."""

    name: str = Field(..., description="Source name identifier")
    type: str = Field(..., description="Source type ('m3u' or 'epg')")
    status: str = Field(
        default="pending",
        description="Source execution status ('pending', 'running', 'success', 'failed', 'skipped')",
    )
    channels: int = Field(default=0, description="Extracted channels count")
    programmes: int = Field(default=0, description="Extracted EPG programmes count")
    duration_s: float = Field(default=0.0, description="Source acquisition duration in seconds")
    engine: str = Field(default="core", description="Ingestion engine used ('pro' or 'core')")
    error: Optional[str] = Field(default=None, description="Optional failure error message")
    reason: Optional[str] = Field(default=None, description="Skip reason (e.g. 'disabled', 'not_in_mode')")


class UpdatePhaseProgress(BaseModel):
    """Progress status of an individual processing pipeline phase."""

    title: str = Field(..., description="Phase title display name")
    status: str = Field(
        default="pending",
        description="Phase execution status ('pending', 'running', 'success', 'failed')",
    )
    detail: Optional[str] = Field(default=None, description="Informational progress detail")


class UpdateProgressSummary(BaseModel):
    """Final metrics summary once acquisition run finishes."""

    status: str = Field(..., description="Overall execution status ('success' or 'failed')")
    duration: float = Field(..., description="Total execution duration in seconds")
    total_channels: int = Field(default=0, description="Total channels processed")
    matched_channels: int = Field(default=0, description="Total channels mapped to EPG")
    channels_modified: int = Field(default=0, description="Total channels modified by rewrites")
    is_turbo_rewrites: bool = Field(default=False, description="Whether Turbo Rewrites engine was active")
    error_message: Optional[str] = Field(default=None, description="Fatal error message if failed")


class UpdateProgressDTO(BaseModel):
    """Unified DTO schema for real-time update progress polling."""

    is_running: bool = Field(default=False, description="Whether an acquisition run is currently active")
    mode: str = Field(default="idle", description="Execution mode ('idle', 'full', 'm3u', 'epg', etc.)")
    elapsed_seconds: float = Field(default=0.0, description="Elapsed execution seconds")
    sources: List[UpdateSourceProgress] = Field(default_factory=list, description="Granular source download progress items")
    phases: Dict[str, UpdatePhaseProgress] = Field(default_factory=dict, description="Pipeline phases progress")
    summary: Optional[UpdateProgressSummary] = Field(default=None, description="Execution summary once finished")



class LoginPayload(BaseModel):
    """Request payload for user authentication login."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class BulkInclusionPayload(BaseModel):
    """Payload for bulk channel inclusion/exclusion."""

    channel_items: List[Dict[str, Any]] = Field(..., description="List of channel items with name and source")
    is_included: bool = Field(..., description="Target inclusion status")


class BulkGroupPayload(BaseModel):
    """Payload for bulk channel group assignment."""

    original_urls: List[str] = Field(..., description="List of channel original_url identity keys")
    group: str = Field(..., description="New group name to set")


class BulkUserAgentPayload(BaseModel):
    """Payload for bulk channel User-Agent assignment."""

    original_urls: List[str] = Field(..., description="List of channel original_url identity keys")
    user_agent: str = Field(..., description="New User-Agent string to set")


class ChannelSearchPayload(BaseModel):
    """Request payload for filtering and paginating processed channels."""

    search: Optional[str] = Field(default=None, description="Filter by channel name search query")
    source: Optional[str] = Field(default=None, description="Filter by IPTV source provider name")
    group: Optional[str] = Field(default=None, description="Filter by group-title")
    is_included: Optional[bool] = Field(default=None, description="Filter by inclusion status")
    is_mapped: Optional[bool] = Field(default=None, description="Filter by EPG mapping status")
    link_status: Optional[str] = Field(default=None, description="Filter by stream link status (online, offline, unchecked)")
    limit: int = Field(default=100, ge=1, le=1000, description="Max items to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class BulkResetRewritesPayload(BaseModel):
    """Payload for bulk resetting individual channel rewrites."""

    original_urls: List[str] = Field(..., description="List of channel original_url identity keys")


class ChannelRewritePayload(BaseModel):
    """Request payload for updating individual channel attribute rewrites."""

    original_url: Optional[str] = Field(default="", description="Channel original URL identity key")
    field: str = Field(..., description="Target attribute field (name, group, logo, url, user_agent)")
    original_val: str = Field(default="", description="Original raw attribute value")
    new_val: str = Field(..., description="New value to set or apply")


class EPGMappingPayload(BaseModel):
    """Request payload for manual channel EPG mapping overrides."""

    channel_name: Optional[str] = Field(default="", description="Target channel display name")
    source_name: Optional[str] = Field(default="", description="IPTV source provider name")
    epg_id: str = Field(..., description="Namespaced EPG channel ID")
    is_global: bool = Field(default=False, description="Apply override globally across all sources")


class NotificationPresetPayload(BaseModel):
    """Request payload for applying a notification preset profile."""

    name: str = Field(..., description="Preset profile name (all, none, simple, balanced, advanced, hardware, content)")


class TestNotificationPayload(BaseModel):
    """Request payload for dispatching a test notification."""

    title: Optional[str] = Field(default="🔔 Pluvira: Test Notification", description="Test notification title")
    body: Optional[str] = Field(default="This is a test notification dispatched from Pluvira.", description="Test notification body")


class EpgProgrammesSearchPayload(BaseModel):
    """Payload for searching EPG programme schedules."""

    ids: List[str] = Field(..., description="List of namespaced EPG channel IDs")
    date: Optional[str] = Field(default=None, description="Filter programmes by specific date (YYYY-MM-DD)")
    date_from: Optional[str] = Field(default=None, description="Filter programmes starting from date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="Filter programmes ending before date (YYYY-MM-DD)")


class ApplyMergePayload(BaseModel):
    """Payload for creating or updating a channel merge configuration."""

    master_name: str = Field(..., description="Canonical master display name")
    primary_stream: StreamRef = Field(..., description="Primary active stream reference")
    backup_streams: List[StreamRef] = Field(default_factory=list, description="Ordered fallback backup streams")
    logo: str = Field(default="", description="Optional logo URL")
    group: str = Field(default="", description="Optional group name")
    epg_id: str = Field(default="", description="Optional EPG ID")


class AutoApplyMergePayload(BaseModel):
    """Payload for high-confidence auto-merge execution."""

    similarity_threshold: float = Field(default=0.95, ge=0.50, le=1.00, description="High-confidence fuzzy similarity threshold")


class MergeClusterSearchPayload(BaseModel):
    """Payload for searching duplicate candidate clusters."""

    similarity_threshold: float = Field(default=0.80, ge=0.50, le=1.00, description="Fuzzy string similarity threshold")


class BulkDeleteMergePayload(BaseModel):
    """Payload for bulk channel unmerge deletion."""

    master_names: List[str] = Field(..., description="List of master channel names to delete")


class BookmarkPayload(BaseModel):
    """Payload for bookmarking a channel from catalog into personal playlist."""

    playlist_id: str = Field(default="default", description="Target personal playlist identifier")
    channel: Dict[str, Any] = Field(..., description="Processed catalog channel dictionary")


class ChannelUpdatePayload(BaseModel):
    """Payload for updating personal channel attributes."""

    name: Optional[str] = Field(default=None, description="Display name")
    logo: Optional[str] = Field(default=None, description="Logo URL")
    epg_id: Optional[str] = Field(default=None, description="EPG ID")
    group: Optional[str] = Field(default=None, description="Category group")
    custom_order: Optional[int] = Field(default=None, description="Custom sort index")
    is_pinned: Optional[bool] = Field(default=None, description="Pinned status")


class SlotReorderPayload(BaseModel):
    """Payload for manually reordering stream slots in a personal channel."""

    slot_ids: List[str] = Field(..., description="Ordered list of slot identifiers")


class PurgePayload(BaseModel):
    """Payload for manual purge of quarantined stream links."""

    playlist_id: Optional[str] = Field(default=None, description="Optional playlist identifier filter")


class PlaylistUpdatePayload(BaseModel):
    """Payload for updating playlist metadata."""

    name: str = Field(..., description="New playlist display name")
    export_token: Optional[str] = Field(default=None, description="Optional updated export token")


class TestLinkPayload(BaseModel):
    """Payload for testing stream link connection."""

    url: str = Field(..., description="Target stream URL to test")
    original_url: Optional[str] = Field(default=None, description="Original URL identity key")
    user_agent: str = Field(default="Mozilla/5.0", description="User-Agent header")


class BatchTestLinkItem(BaseModel):
    """Individual item for batch link testing."""

    url: str = Field(..., description="Stream URL to test")
    original_url: str = Field(..., description="Original URL identity key")
    source: str = Field(..., description="Source name")
    user_agent: Optional[str] = Field(default="Mozilla/5.0", description="User-Agent header")


class BatchTestLinkPayload(BaseModel):
    """Payload for batch stream link testing."""

    items: List[BatchTestLinkItem] = Field(..., description="List of items to test in batch")


class LinkStatusReportPayload(BaseModel):
    """Payload for reporting stream playback status directly from client video player."""

    original_url: str = Field(..., description="Channel original URL identity key")
    link_status: str = Field(..., description="Stream status: online, offline, unchecked, redirect")
    code: int = Field(default=0, description="HTTP status code or client playback error code")
    cors_supported: bool = Field(default=False, description="Whether stream supports direct browser CORS playback")
    needs_proxy: bool = Field(default=False, description="Whether stream requires backend CORS proxy")
    error_message: Optional[str] = Field(default=None, description="Optional playback client error description")
    source: Optional[str] = Field(default=None, description="IPTV source provider name")
    url: Optional[str] = Field(default=None, description="Actual tested stream URL")


class ScheduleJob(BaseModel):
    """Configuration model for an individual background scheduled task."""

    id: str = Field(..., description="Unique job identifier")
    enabled: bool = Field(default=True, description="Whether this job is enabled")
    mode: str = Field(default="tv_sync_full", description="Task execution mode identifier")
    trigger: str = Field(default="cron", description="Trigger type ('cron' or 'interval')")
    hour: Optional[int] = Field(default=4, ge=0, le=23, description="Hour of execution (0-23 UTC)")
    minute: Optional[int] = Field(default=0, ge=0, le=59, description="Minute of execution (0-59)")
    day_of_week: Optional[str] = Field(default="*", description="Cron day of week filter string")
    hours: Optional[int] = Field(default=0, ge=0, description="Interval hours")
    minutes: Optional[int] = Field(default=0, ge=0, description="Interval minutes")
    description: Optional[str] = Field(default="", description="Human-readable job description")
    is_system: bool = Field(default=False, description="Whether this task is a protected system job")
    is_recommended: bool = Field(default=False, description="Whether this task is a recommended factory preset")
    link_test_filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters for link testing")

    @model_validator(mode="after")
    def validate_system_job_constraints(self) -> "ScheduleJob":
        """Enforces safe execution intervals for critical system tasks."""
        if self.is_system and self.mode in ("license_auto_renewal", "license_heartbeat"):
            if self.trigger == "interval":
                total_minutes = (self.hours or 0) * 60 + (self.minutes or 0)
                if total_minutes < 1:
                    raise ValueError("System heartbeat interval must be at least 1 minute")
                if total_minutes > 1440:
                    raise ValueError("System heartbeat interval must not exceed 24 hours")
        return self


class JobMetadataDTO(BaseModel):
    """Metadata model describing a registered background scheduler job."""

    mode: str = Field(..., description="Unique execution mode identifier")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Job purpose description")
    is_system: bool = Field(default=False, description="Whether job is protected system task")
    is_recommended: bool = Field(default=False, description="Whether job is recommended system preset")


class SchedulePayload(BaseModel):
    """Request payload for updating background scheduler configuration."""

    enabled: bool = Field(default=True, description="Enable or disable automated scheduler")
    jobs: List[Dict[str, Any]] = Field(default_factory=list, description="List of scheduled job configurations")


class SystemUpdatePayload(BaseModel):
    """Request payload for triggering background system update."""

    mode: str = Field(default="full", description="Execution mode ('full', 'raw', 'm3u', 'epg')")


class TrialClaimPayload(BaseModel):
    """Payload for claiming on-demand 14-day Pro trial license."""

    token: Optional[str] = Field(default=None, description="Optional signed Ed25519 trial token")
    cloud_url: Optional[str] = Field(default=None, description="Optional custom cloud endpoint URL")


class ActivateLicensePayload(BaseModel):
    """Request payload for activating a commercial Pro license token."""

    token: str = Field(..., min_length=1, description="Signed Ed25519 JWT license token")


class LicenseDetails(BaseModel):
    """Model representing active license status, polymorphic tier, and entitlements."""

    valid: bool = Field(default=False, description="Whether license signature and validity are active")
    status: str = Field(default="success", description="Verification status string")
    error_code: Optional[str] = Field(default=None, description="Standardized IPC error code if failed")
    message: str = Field(default="", description="Human-readable status description")
    license_status: str = Field(default="unlicensed", description="Lifecycle state ('valid', 'expiring_soon', 'grace_period', 'expired', 'unlicensed')")
    tier: str = Field(default="core", description="Dynamic subscription tier slug (e.g. 'core', 'pro', 'ultra', 'enterprise')")
    display_name_full: Optional[str] = Field(default=None, description="Commercial display name of the subscription tier")
    badge_icon: Optional[str] = Field(default="sparkles", description="Lucide icon identifier for UI badge")
    badge_color: Optional[str] = Field(default=None, description="Color code or token for UI badge")
    compact_name: Optional[str] = Field(default=None, description="Compact badge label string for sidebars and small viewports")
    badge_text_color: Optional[str] = Field(default=None, description="Custom text color hex or token for contrast against badge background")
    max_ips: Optional[int] = Field(default=2, description="Maximum concurrent IP stream quota")
    max_slots: Optional[int] = Field(default=None, description="Custom maximum failover slots ceiling")
    backup_max_slots: Optional[int] = Field(default=None, description="Maximum E2EE cloud backup snapshots allowed")
    days_remaining: Optional[int] = Field(default=None, description="Days remaining until expiration")
    expires_at: Optional[int] = Field(default=None, description="Epoch expiration timestamp")
    modules: List[str] = Field(default_factory=list, description="Enabled capability module slugs")
    subject: Optional[str] = Field(default=None, description="Licensed subject identifier or email")
    is_cached: bool = Field(default=False, description="Whether license is loaded from offline cache")
    trial: bool = Field(default=False, description="Whether token is an evaluation trial")
    is_trial: Optional[bool] = Field(default=None, description="Trial alias")
    trial_days_remaining: Optional[int] = Field(default=None, description="Remaining trial days")
    pro_version: Optional[str] = Field(default=None, description="Pro engine version")
    update_recommended: bool = Field(default=False, description="Whether update is recommended")
    crockford_id: Optional[str] = Field(default=None, description="Linked Crockford Base32 user ID")
    cloud_account_linked: bool = Field(default=False, description="Whether linked to cloud account")
    has_claimed_trial: bool = Field(default=False, description="Anti-abuse trial claim flag")
    grace_hours_remaining: Optional[int] = Field(default=None, description="Offline grace period remaining hours")

    @field_validator("tier")
    @classmethod
    def validate_tier_slug(cls, value: str) -> str:
        """Validates tier slug format conforming to ^[a-z0-9_\\-]{2,32}$."""
        if value:
            cleaned = value.strip().lower()
            if not re.match(r"^[a-z0-9_\-]{2,32}$", cleaned):
                raise ValueError("Tier must be a valid lowercase slug (2-32 chars: a-z, 0-9, _, -)")
            return cleaned
        return "core"

    @model_validator(mode="after")
    def sync_trial_fields(self) -> "LicenseDetails":
        if self.is_trial is None:
            self.is_trial = self.trial
        return self


class LicenseActivationDTO(BaseModel):
    """Response DTO for license token activation."""

    success: bool = Field(..., description="Whether license activation was successful")
    message: str = Field(..., description="Human-readable result message")
    license: Optional[Union[LicenseDetails, Dict[str, Any]]] = Field(default=None, description="Detailed license metadata if valid")
    error_code: Optional[str] = Field(default=None, description="Standardized error code on failure")


LicenseActivationResponse = LicenseActivationDTO


class EnvironmentInfoDTO(BaseModel):
    """Model representing runtime environment and version diagnostics."""

    version: str = Field(..., description="Application release version or git tag")
    git_hash: Optional[str] = Field(default=None, description="Short commit git hash")
    config_path: str = Field(..., description="Resolved path to configuration file")
    data_dir: str = Field(..., description="Resolved path to data directory")
    temp_dir: str = Field(..., description="Resolved path to temporary RAM disk directory")



class CloudPairingStartResponse(BaseModel):
    """Response returned when initiating device pairing flow (RFC 8628)."""

    device_code: str = Field(..., description="Opaque device verification code")
    user_code: str = Field(..., description="Short user verification code (e.g. WDJB-MJHT)")
    verification_uri: str = Field(..., description="URL where user enters code")
    verification_uri_complete: str = Field(..., description="URL with embedded user code")
    expires_in: int = Field(default=600, description="Lifetime in seconds of device and user codes")
    interval: int = Field(default=5, description="Minimum polling interval in seconds")


class CloudPairingStatusResponse(BaseModel):
    """Current state of device authorization pairing session."""

    status: str = Field(
        default="idle",
        description="Pairing status: idle, pending, success, expired, denied, failed",
    )
    user_code: Optional[str] = Field(default=None, description="Active user code")
    verification_uri_complete: Optional[str] = Field(default=None, description="Direct pairing URL")
    expires_at: Optional[float] = Field(default=None, description="Epoch timestamp when session expires")
    uid: Optional[str] = Field(default=None, description="Centralized Crockford Base32 User ID")
    formatted_id: Optional[str] = Field(default=None, description="Human-formatted Crockford ID (XXXX-XXXX-XXXX)")
    error_message: Optional[str] = Field(default=None, description="Error message if pairing failed")


class CloudBackupSnapshotItem(BaseModel):
    """Model representing an E2EE backup snapshot stored in Pluvira Cloud vault."""

    id: str = Field(..., description="Unique snapshot identifier")
    size_bytes: int = Field(..., description="Encrypted snapshot size in bytes")
    sha256_checksum: str = Field(..., description="SHA-256 integrity checksum")
    snapshot_label: Optional[str] = Field(default="", description="User-supplied label or description")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    is_pinned: bool = Field(default=False, description="Whether snapshot is locked against FIFO auto-purge")


class CloudBackupUploadPayload(BaseModel):
    """Request payload for uploading a client-side encrypted backup blob to cloud vault."""

    encrypted_blob: Optional[str] = Field(default=None, description="Base64 encoded AES-256-GCM encrypted snapshot")
    encrypted_blob_b64: Optional[str] = Field(default=None, description="Base64 encoded snapshot alias")

    @model_validator(mode="after")
    def sync_blob_fields(self) -> "CloudBackupUploadPayload":
        blob = self.encrypted_blob_b64 or self.encrypted_blob or ""
        self.encrypted_blob = blob
        self.encrypted_blob_b64 = blob
        return self
    sha256_checksum: str = Field(..., min_length=64, max_length=64, description="Hexadecimal SHA-256 integrity checksum")
    snapshot_label: Optional[str] = Field(default="Manual Cloud Backup", description="Optional snapshot label")


class CloudBackupCreateUploadPayload(BaseModel):
    """Request payload for exporting, encrypting, and uploading a backup snapshot via local backend."""

    passphrase: str = Field(..., min_length=8, description="User private encryption passphrase")
    snapshot_label: Optional[str] = Field(default="Manual Cloud Backup", description="Optional snapshot label")
    pin_snapshot: bool = Field(default=False, description="Pin snapshot immediately after upload")


class CloudBackupDecryptPayload(BaseModel):
    """Request payload for downloading and decrypting a cloud backup snapshot via local backend."""

    backup_id: str = Field(..., min_length=1, description="Snapshot identifier in cloud vault")
    passphrase: str = Field(..., min_length=1, description="User private decryption passphrase")


class CloudBackupUploadResponse(BaseModel):
    """Response returned upon successful cloud backup upload."""

    id: str = Field(..., description="Assigned snapshot identifier")
    size_bytes: int = Field(..., description="Stored blob size in bytes")
    sha256_checksum: str = Field(..., description="Verified SHA-256 checksum")
    snapshot_label: Optional[str] = Field(default="", description="Snapshot label")
    created_at: str = Field(..., description="Creation timestamp")
    is_pinned: bool = Field(default=False, description="Whether snapshot is pinned")
    message: str = Field(default="Cloud backup snapshot uploaded successfully", description="Status message")


class CloudBackupPinPayload(BaseModel):
    """Request payload for updating cloud backup snapshot pinning state."""

    is_pinned: bool = Field(..., description="Target pinning lock state")


class CloudBackupLatestDecryptPayload(BaseModel):
    """Request payload for downloading and decrypting latest cloud backup snapshot."""

    passphrase: str = Field(..., min_length=1, description="Decryption passphrase")


class CloudAccountInfo(BaseModel):
    """Model representing linked Pluvira Cloud account information."""

    uid: Optional[str] = Field(default=None, description="Centralized Crockford Base32 User ID")
    formatted_id: Optional[str] = Field(default=None, description="Formatted Crockford Base32 ID")
    access_token: Optional[str] = Field(default=None, description="OIDC Bearer access token")
    linked_at: Optional[str] = Field(default=None, description="ISO timestamp when account was paired")
    is_linked: bool = Field(default=False, description="Whether instance is linked to Pluvira Cloud")
    device_hash: Optional[str] = Field(default=None, description="Hexadecimal SHA-256 device hash fingerprint")


class BulletinMediaDTO(BaseModel):
    """Media attachment model for system bulletin."""

    type: str = Field(default="image", description="Media type (e.g. 'image', 'video')")
    url: str = Field(..., description="External or proxied media URL")
    sha256: str = Field(..., description="SHA-256 integrity checksum")
    alt: Optional[str] = Field(default="", description="Alternative text description")


class BulletinDTO(BaseModel):
    """System bulletin broadcast DTO."""

    id: str = Field(..., description="Unique immutable bulletin identifier")
    level: str = Field(default="info", description="Severity level: info, warning, critical, security")
    icon: Optional[str] = Field(default="sparkles", description="Lucide icon identifier")
    title: Dict[str, str] = Field(..., description="Multilingual title dictionary")
    message: Dict[str, str] = Field(..., description="Multilingual Safe-Markdown text dictionary")
    action_url: Optional[str] = Field(default=None, description="Action URL")
    action_label: Optional[Dict[str, str]] = Field(default=None, description="Multilingual button label dictionary")
    media: Optional[BulletinMediaDTO] = Field(default=None, description="Optional media attachment")
    dismissible: bool = Field(default=True, description="Whether bulletin can be dismissed")
    priority: int = Field(default=0, description="Priority integer sorting key")
    expires_at: int = Field(..., description="UTC epoch expiration timestamp")
    signature: Optional[str] = Field(default=None, description="Detached Ed25519 signature for security advisories")
    is_dismissed: bool = Field(default=False, description="Whether bulletin has been dismissed locally")
    dismissed_at: Optional[str] = Field(default=None, description="ISO timestamp of local dismissal")
    is_read: bool = Field(default=False, description="Whether bulletin has been rendered/viewed in UI")
    read_at: Optional[str] = Field(default=None, description="ISO timestamp of local view")


class BulletinListResponse(BaseModel):
    """Response container for active system bulletins."""

    bulletins: List[BulletinDTO] = Field(default_factory=list, description="Active bulletin items")
    total: int = Field(default=0, description="Total active bulletins count")
    unread_count: int = Field(default=0, description="Unread/un-dismissed bulletins count")


class BulletinDismissResponse(BaseModel):
    """Response DTO for bulletin dismissal."""

    id: str = Field(..., description="Bulletin ID")
    is_dismissed: bool = Field(default=True, description="Dismissal status")
    message: str = Field(default="Bulletin dismissed successfully", description="Status message")


class BulletinReadResponse(BaseModel):
    """Response DTO for bulletin read acknowledgment."""

    id: str = Field(..., description="Bulletin ID")
    is_read: bool = Field(default=True, description="Read status")
    message: str = Field(default="Bulletin marked as read successfully", description="Status message")


class BulletinAckPayload(BaseModel):
    """Container for bulletin lifecycle event acknowledgments."""

    received: List[str] = Field(
        default_factory=list,
        description="Bulletin IDs downloaded and safely persisted in local SQLite WAL",
    )
    read: List[str] = Field(
        default_factory=list,
        description="Bulletin IDs actually rendered/viewed in UI viewport",
    )
    dismissed: List[str] = Field(
        default_factory=list,
        description="Bulletin IDs explicitly dismissed with close action",
    )


class AutoMapEpgPayload(BaseModel):
    """Payload for automatic channel EPG guide mapping."""

    scope: str = Field(default="curated", description="Target scope: 'curated' (My List) or 'all' (catalog)")
    playlist_id: str = Field(default="default", description="Target curated playlist identifier")
    similarity_threshold: float = Field(default=0.85, ge=0.50, le=1.00, description="Minimum matching threshold")
    overwrite_existing: bool = Field(default=False, description="Whether to overwrite existing manual EPG mappings")
    source: Optional[str] = Field(default=None, description="Optional IPTV source name filter")
    only_unmapped: bool = Field(default=True, description="Only match channels currently lacking an EPG mapping")


class AutoMapEpgOverrideItem(BaseModel):
    """Individual applied EPG mapping override detail."""

    channel_name: str = Field(..., description="Target channel display name")
    source_name: str = Field(default="", description="IPTV source provider name")
    epg_id: str = Field(..., description="Mapped namespaced EPG channel ID")


class AutoMapEpgResponse(BaseModel):
    """Response model for automatic channel EPG guide mapping."""

    success: bool = Field(default=True, description="Whether execution was successful")
    scope: str = Field(default="curated", description="Applied channel scope")
    total_evaluated: int = Field(default=0, description="Total candidate channels evaluated")
    mapped_count: int = Field(default=0, description="Number of channels successfully mapped")
    matched_count: int = Field(default=0, description="Alias for mapped_count")
    skipped_count: int = Field(default=0, description="Number of candidate channels skipped or unmapped")
    is_pro: bool = Field(default=False, description="Whether Pro matching engine was active")
    message: str = Field(default="", description="Human-readable result summary")
    applied_overrides: List[AutoMapEpgOverrideItem] = Field(default_factory=list, description="Applied mapping overrides")

    @model_validator(mode="before")
    @classmethod
    def sync_counts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "mapped_count" in data and "matched_count" not in data:
                data["matched_count"] = data["mapped_count"]
            elif "matched_count" in data and "mapped_count" not in data:
                data["mapped_count"] = data["matched_count"]
        return data
