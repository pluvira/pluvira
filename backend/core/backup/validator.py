"""Pre-flight validation and structured diff calculation engine for configuration backups."""

from typing import Dict, Any, List, Union, Optional
from copy import deepcopy

from backend.config.models import (
    GlobalConfig,
    SourceSettings,
    AuthConfig,
    RewriteRule,
    ChannelMerge,
)
from backend.core.backup.bundle import (
    BackupBundle,
    BackupValidationResult,
    BackupDiffSummary,
    DiffCategoryCount,
)
from backend.core.backup.sanitizer import BackupSanitizer
from backend.core.backup.migrator import CURRENT_SCHEMA_VERSION


class BackupValidator:
    """Validates backup bundle structure, checks schema version compatibility, and generates diffs."""

    @classmethod
    def validate_bundle(
        cls,
        bundle_input: Union[Dict[str, Any], BackupBundle],
        existing_config: GlobalConfig,
        existing_schedule: Dict[str, Any],
        mode: str = "destructive",
        existing_individual_rewrites: Optional[Dict[str, List[RewriteRule]]] = None,
        existing_channel_merges: Optional[Dict[str, ChannelMerge]] = None,
        existing_epg_overrides: Optional[List[Dict[str, Any]]] = None,
        existing_source_filters: Optional[List[Dict[str, Any]]] = None,
        existing_metadata_rules: Optional[List[Dict[str, Any]]] = None,
        existing_notification_targets: Optional[List[str]] = None,
        existing_notification_settings: Optional[Dict[str, Any]] = None,
        existing_sources: Optional[List[Dict[str, Any]]] = None,
        existing_epg_sources: Optional[List[Dict[str, Any]]] = None,
        existing_playlists: Optional[List[Dict[str, Any]]] = None,
        existing_personal_channels: Optional[List[Dict[str, Any]]] = None,
    ) -> BackupValidationResult:
        """Performs pre-flight validation and diff analysis on incoming backup bundle.

        Args:
            bundle_input (Union[Dict[str, Any], BackupBundle]): Raw dictionary or BackupBundle object.
            existing_config (GlobalConfig): Active configuration currently on disk.
            existing_schedule (Dict[str, Any]): Active schedule configuration currently on disk.
            mode (str): Import mode ('destructive' or 'merge').

        Returns:
            BackupValidationResult: Validation report containing validity, errors, warnings, and diff summary.
        """
        errors: List[str] = []
        warnings: List[str] = []

        clean_mode = mode.lower().strip()
        if clean_mode not in ("destructive", "merge"):
            errors.append(f"Invalid import mode '{mode}'. Supported modes are 'destructive' and 'merge'.")

        bundle: BackupBundle
        bundle_version = 1
        if isinstance(bundle_input, BackupBundle):
            bundle = bundle_input
            bundle_version = bundle.bundle_version
        elif isinstance(bundle_input, dict):
            bundle_dict = deepcopy(bundle_input)
            raw_v = bundle_dict.get("bundle_version", 1)
            try:
                bundle_version = int(raw_v) if raw_v is not None and raw_v != "" else 1
                if bundle_version < 1:
                    bundle_version = 1
            except (ValueError, TypeError):
                bundle_version = 1
            if bundle_version > CURRENT_SCHEMA_VERSION:
                errors.append(
                    f"Unsupported bundle schema version {bundle_version}. Max supported version is {CURRENT_SCHEMA_VERSION}."
                )
            try:
                bundle = BackupBundle.model_validate(bundle_dict)
            except Exception as e:
                errors.append(f"Bundle structural validation failed: {e}")
                return BackupValidationResult(
                    valid=False,
                    bundle_version=bundle_version,
                    target_version=CURRENT_SCHEMA_VERSION,
                    migration_required=bundle_version < CURRENT_SCHEMA_VERSION,
                    errors=errors,
                    warnings=warnings,
                    diff=None,
                )
        else:
            errors.append("Invalid bundle payload type.")
            return BackupValidationResult(
                valid=False,
                bundle_version=1,
                target_version=CURRENT_SCHEMA_VERSION,
                errors=errors,
                warnings=warnings,
                diff=None,
            )

        if bundle_version > CURRENT_SCHEMA_VERSION:
            errors.append(
                f"Unsupported bundle schema version {bundle_version}. Max supported version is {CURRENT_SCHEMA_VERSION}."
            )

        migration_required = bundle_version < CURRENT_SCHEMA_VERSION
        if migration_required:
            warnings.append(
                f"Bundle schema version {bundle_version} is older than current version {CURRENT_SCHEMA_VERSION}. Automatic schema migration will be applied."
            )

        sanitized_detected = bundle.sanitized
        if not sanitized_detected and bundle.config.auth:
            if BackupSanitizer.is_sanitized_value(bundle.config.auth.password) or BackupSanitizer.is_sanitized_value(
                bundle.config.auth.secret_key
            ):
                sanitized_detected = True

        if sanitized_detected:
            warnings.append(
                "Sanitized credentials detected in bundle. Active credentials on disk will be preserved on import."
            )

        diff = cls._calculate_diff(
            bundle,
            existing_config,
            existing_schedule,
            clean_mode,
            existing_individual_rewrites,
            existing_channel_merges,
            existing_epg_overrides,
            existing_source_filters,
            existing_metadata_rules,
            existing_notification_targets,
            existing_notification_settings,
            existing_sources,
            existing_epg_sources,
            existing_playlists,
            existing_personal_channels,
        )

        return BackupValidationResult(
            valid=len(errors) == 0,
            bundle_version=bundle_version,
            target_version=CURRENT_SCHEMA_VERSION,
            migration_required=migration_required,
            sanitized_detected=sanitized_detected,
            errors=errors,
            warnings=warnings,
            diff=diff if len(errors) == 0 else None,
        )

    @classmethod
    def _calculate_diff(
        cls,
        bundle: BackupBundle,
        existing_config: GlobalConfig,
        existing_schedule: Dict[str, Any],
        mode: str,
        existing_individual_rewrites: Optional[Dict[str, List[RewriteRule]]] = None,
        existing_channel_merges: Optional[Dict[str, ChannelMerge]] = None,
        existing_epg_overrides: Optional[List[Dict[str, Any]]] = None,
        existing_source_filters: Optional[List[Dict[str, Any]]] = None,
        existing_metadata_rules: Optional[List[Dict[str, Any]]] = None,
        existing_notification_targets: Optional[List[str]] = None,
        existing_notification_settings: Optional[Dict[str, Any]] = None,
        existing_sources: Optional[List[Dict[str, Any]]] = None,
        existing_epg_sources: Optional[List[Dict[str, Any]]] = None,
        existing_playlists: Optional[List[Dict[str, Any]]] = None,
        existing_personal_channels: Optional[List[Dict[str, Any]]] = None,
    ) -> BackupDiffSummary:
        """Calculates structured diff between existing state and incoming bundle."""
        cfg = bundle.config
        incoming_sources = getattr(bundle, "sources", None) or [s.model_dump() for s in cfg.sources]
        sources_list = existing_sources if existing_sources is not None else [s.model_dump() for s in existing_config.sources]
        sources_diff = cls._diff_named_entities(
            sources_list,
            incoming_sources,
            key_attr="name",
            mode=mode,
        )

        incoming_epg = getattr(bundle, "epg_sources", None) or [s.model_dump() for s in cfg.epg_sources]
        epg_sources_list = existing_epg_sources if existing_epg_sources is not None else [s.model_dump() for s in existing_config.epg_sources]
        epg_sources_diff = cls._diff_named_entities(
            epg_sources_list,
            incoming_epg,
            key_attr="name",
            mode=mode,
        )

        existing_rewrites = (
            existing_individual_rewrites
            if existing_individual_rewrites is not None
            else (getattr(existing_config, "individual_rewrites", {}) or {})
        )
        incoming_rewrites = (
            getattr(bundle, "individual_rewrites", {})
            or getattr(cfg, "individual_rewrites", {})
            or {}
        )
        individual_rewrites_diff = cls._diff_dict_keys(
            existing_rewrites or {},
            incoming_rewrites or {},
            mode=mode,
        )

        existing_merges = (
            existing_channel_merges
            if existing_channel_merges is not None
            else (getattr(existing_config, "channel_merges", {}) or {})
        )
        incoming_merges = (
            getattr(bundle, "channel_merges", {})
            or getattr(cfg, "channel_merges", {})
            or {}
        )
        channel_merges_diff = cls._diff_dict_keys(
            existing_merges or {},
            incoming_merges or {},
            mode=mode,
        )

        existing_pl = existing_playlists if existing_playlists is not None else []
        incoming_pl = getattr(bundle, "playlists", []) or []
        playlists_diff = cls._diff_named_entities(
            existing_pl,
            incoming_pl,
            key_attr="id",
            mode=mode,
        )

        existing_pch = existing_personal_channels if existing_personal_channels is not None else []
        incoming_pch = getattr(bundle, "personal_channels", []) or []
        personal_channels_diff = cls._diff_named_entities(
            existing_pch,
            incoming_pch,
            key_attr="id",
            mode=mode,
        )

        existing_overrides = existing_epg_overrides if existing_epg_overrides is not None else []
        incoming_overrides = getattr(bundle, "epg_mapping_overrides", []) or []
        epg_mapping_overrides_diff = cls._diff_named_entities(
            [{"key": f"{o.get('channel_name')}::{o.get('source_name', '')}", **o} for o in existing_overrides],
            [{"key": f"{o.get('channel_name')}::{o.get('source_name', '')}", **o} for o in incoming_overrides],
            key_attr="key",
            mode=mode,
        )

        existing_filters = existing_source_filters if existing_source_filters is not None else []
        incoming_filters = getattr(bundle, "source_channel_filters", []) or []
        source_channel_filters_diff = cls._diff_named_entities(
            [{"key": f"{f.get('source_name')}::{f.get('channel_name')}::{f.get('filter_type')}", **f} for f in existing_filters],
            [{"key": f"{f.get('source_name')}::{f.get('channel_name')}::{f.get('filter_type')}", **f} for f in incoming_filters],
            key_attr="key",
            mode=mode,
        )

        existing_meta = existing_metadata_rules if existing_metadata_rules is not None else []
        incoming_meta = getattr(bundle, "metadata_rules", []) or []
        metadata_rules_diff = cls._diff_named_entities(
            [{"key": f"{r.get('tier')}::{r.get('source_name', '')}::{r.get('field')}::{r.get('pattern', '')}", **r} for r in existing_meta],
            [{"key": f"{r.get('tier')}::{r.get('source_name', '')}::{r.get('field')}::{r.get('pattern', '')}", **r} for r in incoming_meta],
            key_attr="key",
            mode=mode,
        )

        existing_jobs = existing_schedule.get("jobs", []) if isinstance(existing_schedule, dict) else []
        incoming_jobs = bundle.schedule.jobs or []
        schedule_jobs_diff = cls._diff_named_entities(
            existing_jobs,
            incoming_jobs,
            key_attr="id",
            mode=mode,
        )

        existing_notif_urls = existing_notification_targets if existing_notification_targets is not None else []
        incoming_notif_urls = getattr(bundle, "notification_targets", []) or []
        notification_targets_diff = cls._diff_named_entities(
            [{"url": u} for u in existing_notif_urls],
            [{"url": u} for u in incoming_notif_urls],
            key_attr="url",
            mode=mode,
        )

        settings_modified = cls._diff_settings(existing_config.settings, cfg.settings)
        auth_modified = cls._diff_auth(existing_config.auth, cfg.auth)
        notifications_modified = (
            getattr(bundle, "notification_settings", None) is not None
            or len(incoming_notif_urls) > 0
        )

        return BackupDiffSummary(
            sources=sources_diff,
            epg_sources=epg_sources_diff,
            individual_rewrites=individual_rewrites_diff,
            channel_merges=channel_merges_diff,
            playlists=playlists_diff,
            personal_channels=personal_channels_diff,
            epg_mapping_overrides=epg_mapping_overrides_diff,
            source_channel_filters=source_channel_filters_diff,
            metadata_rules=metadata_rules_diff,
            schedule_jobs=schedule_jobs_diff,
            notification_targets=notification_targets_diff,
            settings_modified=settings_modified,
            auth_modified=auth_modified,
            notifications_modified=notifications_modified,
        )

    @staticmethod
    def _diff_named_entities(
        existing_items: List[Dict[str, Any]],
        incoming_items: List[Dict[str, Any]],
        key_attr: str = "name",
        mode: str = "destructive",
    ) -> DiffCategoryCount:
        """Computes added, updated, and removed counts for list of entity dictionaries."""
        existing_map = {item.get(key_attr): item for item in existing_items if item.get(key_attr)}
        incoming_map = {item.get(key_attr): item for item in incoming_items if item.get(key_attr)}

        added = sum(1 for k in incoming_map if k not in existing_map)
        updated = sum(1 for k, v in incoming_map.items() if k in existing_map and v != existing_map[k])
        removed = sum(1 for k in existing_map if k not in incoming_map) if mode == "destructive" else 0

        return DiffCategoryCount(added=added, updated=updated, removed=removed)

    @staticmethod
    def _diff_dict_keys(
        existing_dict: Dict[str, Any],
        incoming_dict: Dict[str, Any],
        mode: str = "destructive",
    ) -> DiffCategoryCount:
        """Computes added, updated, and removed counts for dictionary key mappings."""
        added = sum(1 for k in incoming_dict if k not in existing_dict)
        updated = sum(1 for k, v in incoming_dict.items() if k in existing_dict and v != existing_dict[k])
        removed = sum(1 for k in existing_dict if k not in incoming_dict) if mode == "destructive" else 0

        return DiffCategoryCount(added=added, updated=updated, removed=removed)

    @staticmethod
    def _diff_settings(existing: SourceSettings, incoming: SourceSettings) -> List[str]:
        """Identifies modified settings fields."""
        fields_to_check = [
            "user_agent",
            "epg_retention_days",
            "cache_driver",
            "cache_ttl_seconds",
            "search_debounce_ms",
            "force_proxy",
            "link_test_settings",
            "notifications",
            "rewrites",
            "filters",
            "allow_channels",
            "deny_channels",
        ]
        modified = []
        for field in fields_to_check:
            val_exist = getattr(existing, field, None)
            val_in = getattr(incoming, field, None)
            if val_exist != val_in:
                modified.append(field)
        return modified

    @staticmethod
    def _diff_auth(existing: AuthConfig, incoming: AuthConfig) -> bool:
        """Checks if authentication configuration differs."""
        if not existing or not incoming:
            return existing != incoming
        return (
            existing.enabled != incoming.enabled
            or existing.username != incoming.username
            or (incoming.password != "" and incoming.password != "***SANITIZED***" and existing.password != incoming.password)
            or (incoming.secret_key != "" and incoming.secret_key != "***SANITIZED***" and existing.secret_key != incoming.secret_key)
        )
