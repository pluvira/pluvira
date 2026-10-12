"""Pydantic schemas for unified backup bundles, validation results, and diff summaries."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.config.models import GlobalConfig, RewriteRule


class BackupScheduleData(BaseModel):
    """Schema representing background scheduler configuration inside backup bundle."""

    version: int = Field(default=1, ge=1, description="Scheduler schema version")
    enabled: bool = Field(default=True, description="Scheduler global enabled flag")
    jobs: List[Dict[str, Any]] = Field(default_factory=list, description="List of configured scheduled jobs")


class BackupBundle(BaseModel):
    """Unified configuration backup bundle containing application config and scheduler state."""

    bundle_version: int = Field(default=1, ge=1, description="Backup bundle format version")
    app_version: str = Field(default="0.1.0", description="Pluvira application version")
    exported_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC export timestamp",
    )
    sanitized: bool = Field(default=False, description="Whether sensitive credentials have been sanitized")
    config: GlobalConfig = Field(..., description="Application GlobalConfig object")
    schedule: BackupScheduleData = Field(default_factory=BackupScheduleData, description="Scheduler configuration")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="IPTV M3U source definitions")
    epg_sources: List[Dict[str, Any]] = Field(default_factory=list, description="XMLTV EPG guide source definitions")
    channel_merges: Dict[str, Any] = Field(default_factory=dict, description="Master channel merges and fallback chains")
    playlists: List[Dict[str, Any]] = Field(default_factory=list, description="Curated personal playlists")
    personal_channels: List[Dict[str, Any]] = Field(default_factory=list, description="Personal channels with slots and suggestions")
    individual_rewrites: Dict[str, List[RewriteRule]] = Field(
        default_factory=dict, description="Individual channel rewrite rules"
    )
    epg_mapping_overrides: List[Dict[str, Any]] = Field(
        default_factory=list, description="EPG mapping override records"
    )
    source_channel_filters: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source channel filter records (allow/deny)"
    )
    metadata_rules: List[Dict[str, Any]] = Field(
        default_factory=list, description="Metadata rewrite rules (global and source tiers)"
    )
    notification_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="System notification settings and event toggles"
    )
    notification_targets: List[str] = Field(
        default_factory=list, description="Target notification webhook URLs"
    )


class DiffCategoryCount(BaseModel):
    """Detailed change count for a specific configuration entity."""

    added: int = Field(default=0, ge=0, description="Count of added items")
    updated: int = Field(default=0, ge=0, description="Count of updated items")
    removed: int = Field(default=0, ge=0, description="Count of removed items")


class BackupDiffSummary(BaseModel):
    """Structured diff summary between active configuration and incoming backup bundle."""

    sources: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    epg_sources: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    individual_rewrites: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    channel_merges: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    playlists: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    personal_channels: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    epg_mapping_overrides: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    source_channel_filters: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    metadata_rules: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    schedule_jobs: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    notification_targets: DiffCategoryCount = Field(default_factory=DiffCategoryCount)
    settings_modified: List[str] = Field(default_factory=list, description="List of modified global settings fields")
    auth_modified: bool = Field(default=False, description="Whether authentication configuration was modified")
    notifications_modified: bool = Field(default=False, description="Whether notification configuration was modified")


class BackupValidationResult(BaseModel):
    """Pre-flight validation report and diff analysis for backup bundle."""

    valid: bool = Field(default=True, description="Whether the backup bundle is valid and compatible")
    bundle_version: int = Field(default=1, ge=1, description="Source bundle schema version")
    target_version: int = Field(default=1, ge=1, description="Current system schema version")
    migration_required: bool = Field(default=False, description="Whether schema migration will be applied")
    sanitized_detected: bool = Field(default=False, description="Whether sanitized placeholders are present in bundle")
    errors: List[str] = Field(default_factory=list, description="List of fatal validation error messages")
    warnings: List[str] = Field(default_factory=list, description="List of non-fatal warnings")
    diff: Optional[BackupDiffSummary] = Field(default=None, description="Detailed configuration diff")


class BackupImportPayload(BaseModel):
    """Request payload for applying backup bundle import."""

    bundle: BackupBundle = Field(..., description="Unified backup bundle object")
    mode: str = Field(default="destructive", description="Import mode ('destructive' or 'merge')")
    trigger_sync: bool = Field(
        default=True,
        description="Automatically trigger background acquisition if enabled sources exist",
    )


class BackupImportResult(BaseModel):
    """Operation report after importing backup bundle."""

    success: bool = Field(default=True, description="Operation success status")
    mode: str = Field(..., description="Applied import mode ('destructive' or 'merge')")
    message: str = Field(..., description="Human-readable result summary")
    snapshot_created: bool = Field(default=True, description="Whether safety rollback snapshot was generated")
    diff: Optional[BackupDiffSummary] = Field(default=None, description="Summary of applied changes")
