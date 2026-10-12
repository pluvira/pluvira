"""Backup service layer encapsulating export, validation, safety snapshots, and atomic import."""

import shutil
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.exceptions import InvalidConfigurationError
from backend.services.system_service import SystemService
from backend.config.models import GlobalConfig, Source, EPGSource
from backend.scheduler.manager import scheduler_manager, SchedulerManager
from backend.core.backup.bundle import (
    BackupBundle,
    BackupScheduleData,
    BackupValidationResult,
    BackupImportResult,
)
from backend.core.backup.sanitizer import BackupSanitizer
from backend.core.backup.migrator import MigrationManager, CURRENT_SCHEMA_VERSION
from backend.core.backup.validator import BackupValidator
from backend.core.individual_rewrite_repository import IndividualRewriteRepository
from backend.core.channel_merge_repository import ChannelMergeRepository
from backend.core.epg_override_repository import EpgOverrideRepository
from backend.core.source_filter_repository import SourceFilterRepository
from backend.core.source_repository import SourceRepository
from backend.core.metadata_rule_repository import MetadataRuleRepository
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.config.settings import settings
from backend.core.db import db_manager


class BackupService:
    """Service handling configuration backups, pre-flight validation, and transactional imports."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        scheduler: Optional[SchedulerManager] = None,
        system_service: Optional[SystemService] = None,
    ) -> None:
        """Initializes backup service.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
            scheduler (Optional[SchedulerManager]): Override scheduler manager instance.
            system_service (Optional[SystemService]): Override system service instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.scheduler_manager = scheduler or scheduler_manager
        self.system_service = system_service or SystemService()
        self.rewrite_repo = IndividualRewriteRepository()
        self.merge_repo = ChannelMergeRepository()
        self.override_repo = EpgOverrideRepository()
        self.source_filter_repo = SourceFilterRepository()
        self.source_repo = SourceRepository()
        self.metadata_rule_repo = MetadataRuleRepository()
        self.personal_repo = PersonalPlaylistRepository(settings.data_dir)
        from backend.core.notification_repository import NotificationRepository
        self.notification_repo = NotificationRepository()

    def _get_existing_playlists(self) -> List[Dict[str, Any]]:
        """Retrieves all personal curated playlists as a list of dicts."""
        return self.personal_repo.get_all_playlists_flat()

    def _get_existing_personal_channels(self) -> List[Dict[str, Any]]:
        """Retrieves all personal curated channels with slots and suggestions as dicts."""
        return self.personal_repo.get_all_channels_with_slots_flat()

    def _persist_playlists_and_channels(
        self,
        incoming_playlists: List[Dict[str, Any]],
        incoming_pchannels: List[Dict[str, Any]],
        destructive: bool = False,
    ) -> None:
        """Persists personal playlists and channels into SQLite tables."""
        self.personal_repo.persist_playlists_and_channels(
            incoming_playlists, incoming_pchannels, destructive=destructive
        )

    def _get_existing_epg_overrides(self) -> List[Dict[str, Any]]:
        """Retrieves all existing EPG mapping overrides as a flat list of dicts."""
        global_map, source_map = self.override_repo.get_all_grouped()
        overrides_list = [{"channel_name": ch, "epg_id": epg, "source_name": ""} for ch, epg in global_map.items()]
        for src, src_ch_map in source_map.items():
            for ch, epg in src_ch_map.items():
                overrides_list.append({"channel_name": ch, "epg_id": epg, "source_name": src})
        return overrides_list

    def _persist_bundle_entities(
        self,
        incoming_bundle: BackupBundle,
        incoming_config: GlobalConfig,
        incoming_rewrites: Dict[str, Any],
        destructive: bool = False,
    ) -> None:
        """Persists relational entities from incoming bundle into SQLite repositories."""
        if destructive:
            self.source_repo.clear_all_sources()
            self.source_repo.clear_all_epg_sources()
            self.rewrite_repo.clear_all()
            self.merge_repo.clear_all()
            self.override_repo.clear_all()
            self.source_filter_repo.clear_all()
            self.metadata_rule_repo.clear_all()
            self.notification_repo.clear_all()

        if incoming_config.sources:
            self.source_repo.bulk_save_sources(incoming_config.sources)
        if incoming_config.epg_sources:
            self.source_repo.bulk_save_epg_sources(incoming_config.epg_sources)

        for url, rules in incoming_rewrites.items():
            for r in rules:
                self.rewrite_repo.set_rule(
                    original_url=url,
                    field=r.field,
                    replacement=r.replacement,
                    mode=r.mode,
                    pattern=r.pattern,
                    enabled=r.enabled,
                    description=r.description,
                )

        incoming_merges = (
            getattr(incoming_bundle, "channel_merges", None)
            or getattr(incoming_config, "channel_merges", {})
            or {}
        )
        from backend.config.models import ChannelMerge
        for m_name, m_cfg in incoming_merges.items():
            m_model = ChannelMerge.model_validate(m_cfg) if isinstance(m_cfg, dict) else m_cfg
            self.merge_repo.save_merge(m_model, master_name=m_name)

        self._persist_playlists_and_channels(
            getattr(incoming_bundle, "playlists", []) or [],
            getattr(incoming_bundle, "personal_channels", []) or [],
            destructive=destructive,
        )

        incoming_overrides = getattr(incoming_bundle, "epg_mapping_overrides", []) or []
        self.override_repo.bulk_set_overrides(incoming_overrides)

        incoming_filters = getattr(incoming_bundle, "source_channel_filters", []) or []
        self.source_filter_repo.bulk_set_all(incoming_filters)

        incoming_meta = getattr(incoming_bundle, "metadata_rules", []) or []
        if incoming_meta:
            self.metadata_rule_repo.bulk_set_all(incoming_meta)
        elif incoming_config.settings and incoming_config.settings.rewrites:
            self.metadata_rule_repo.set_global_rules(incoming_config.settings.rewrites)

        incoming_notif_dict = getattr(incoming_bundle, "notification_settings", None)
        incoming_targets = getattr(incoming_bundle, "notification_targets", []) or []
        if incoming_notif_dict:
            from backend.config.models import NotificationSettings
            n_set = NotificationSettings.model_validate(incoming_notif_dict)
            if incoming_targets:
                if destructive:
                    if not n_set.urls:
                        n_set.urls = incoming_targets
                else:
                    for t in incoming_targets:
                        if t not in n_set.urls:
                            n_set.urls.append(t)
            self.notification_repo.save_settings(n_set)
        elif incoming_targets:
            if destructive:
                from backend.config.models import NotificationSettings
                self.notification_repo.save_settings(NotificationSettings(enabled=False, urls=incoming_targets))
            else:
                for t in incoming_targets:
                    self.notification_repo.add_url(t)

    def export_backup(self, sanitized: bool = False) -> BackupBundle:
        """Generates unified backup bundle containing configuration and scheduler settings.

        Args:
            sanitized (bool): Whether to mask sensitive credentials and webhook tokens.

        Returns:
            BackupBundle: Serialized unified backup bundle.
        """
        config = self.config_handler.load_config()
        repo_sources = self.source_repo.get_all_sources()
        if repo_sources:
            config.sources = repo_sources
        repo_epg_sources = self.source_repo.get_all_epg_sources()
        if repo_epg_sources:
            config.epg_sources = repo_epg_sources
        config.channel_merges = self.merge_repo.get_all()
        schedule_raw = self.scheduler_manager.get_config()

        schedule_data = BackupScheduleData(
            version=schedule_raw.get("version", CURRENT_SCHEMA_VERSION),
            enabled=schedule_raw.get("enabled", True),
            jobs=schedule_raw.get("jobs", []),
        )

        bundle = BackupBundle(
            bundle_version=CURRENT_SCHEMA_VERSION,
            app_version="0.1.0",
            exported_at=datetime.now(timezone.utc).isoformat(),
            sanitized=False,
            config=config,
            schedule=schedule_data,
            sources=[s.model_dump() for s in repo_sources],
            epg_sources=[s.model_dump() for s in repo_epg_sources],
            channel_merges={k: v.model_dump() for k, v in self.merge_repo.get_all().items()},
            playlists=self._get_existing_playlists(),
            personal_channels=self._get_existing_personal_channels(),
            individual_rewrites=self.rewrite_repo.get_all_grouped(),
            epg_mapping_overrides=self._get_existing_epg_overrides(),
            source_channel_filters=self.source_filter_repo.get_all_flat(),
            metadata_rules=self.metadata_rule_repo.get_all_rules_flat(),
            notification_settings=self.notification_repo.get_settings().model_dump(),
            notification_targets=self.notification_repo.get_urls(),
        )

        if sanitized:
            return BackupSanitizer.sanitize_bundle(bundle)

        return bundle

    def validate_backup(
        self,
        bundle_input: Union[Dict[str, Any], BackupBundle],
        mode: str = "destructive",
    ) -> BackupValidationResult:
        """Performs pre-flight validation and diff analysis against current disk state.

        Args:
            bundle_input (Union[Dict[str, Any], BackupBundle]): Incoming bundle dictionary or model.
            mode (str): Import mode ('destructive' or 'merge').

        Returns:
            BackupValidationResult: Detailed validation report and diff summary.
        """
        existing_config = self.config_handler.load_config()
        existing_schedule = self.scheduler_manager.get_config()

        return BackupValidator.validate_bundle(
            bundle_input=bundle_input,
            existing_config=existing_config,
            existing_schedule=existing_schedule,
            mode=mode,
            existing_individual_rewrites=self.rewrite_repo.get_all_grouped(),
            existing_channel_merges=self.merge_repo.get_all(),
            existing_epg_overrides=self._get_existing_epg_overrides(),
            existing_source_filters=self.source_filter_repo.get_all_flat(),
            existing_metadata_rules=self.metadata_rule_repo.get_all_rules_flat(),
            existing_notification_targets=self.notification_repo.get_urls(),
            existing_notification_settings=self.notification_repo.get_settings().model_dump(),
            existing_sources=[s.model_dump() for s in self.source_repo.get_all_sources()],
            existing_epg_sources=[s.model_dump() for s in self.source_repo.get_all_epg_sources()],
            existing_playlists=self._get_existing_playlists(),
            existing_personal_channels=self._get_existing_personal_channels(),
        )

    def import_backup(
        self,
        bundle_input: Union[Dict[str, Any], BackupBundle],
        mode: str = "destructive",
        trigger_sync: bool = False,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> BackupImportResult:
        """Imports and persists backup bundle with transactional safety snapshots and auto-rollback.

        Args:
            bundle_input (Union[Dict[str, Any], BackupBundle]): Incoming bundle object.
            mode (str): Import mode ('destructive' or 'merge').

        Returns:
            BackupImportResult: Import execution report with diff summary.

        Raises:
            HTTPException: 400 Bad Request if bundle is invalid or unsupported.
            HTTPException: 500 Internal Server Error if persistence or rollback fails.
        """
        clean_mode = mode.lower().strip()
        existing_config = self.config_handler.load_config()
        existing_schedule = self.scheduler_manager.get_config()

        val_result = BackupValidator.validate_bundle(
            bundle_input=bundle_input,
            existing_config=existing_config,
            existing_schedule=existing_schedule,
            mode=clean_mode,
        )

        if not val_result.valid:
            raise InvalidConfigurationError(f"Backup validation failed: {'; '.join(val_result.errors)}")

        raw_sources: List[Source] = []
        raw_epg_sources: List[EPGSource] = []
        bundle_dict: Dict[str, Any]
        if isinstance(bundle_input, BackupBundle):
            raw_sources = list(bundle_input.config.sources)
            raw_epg_sources = list(bundle_input.config.epg_sources)
            bundle_dict = bundle_input.model_dump()
        else:
            bundle_dict = dict(bundle_input)
            if "config" in bundle_dict and isinstance(bundle_dict["config"], dict):
                raw_sources = [Source.model_validate(s) for s in bundle_dict["config"].get("sources", [])]
                raw_epg_sources = [EPGSource.model_validate(s) for s in bundle_dict["config"].get("epg_sources", [])]

        migrated_bundle_dict, _ = MigrationManager.migrate_bundle_dict(bundle_dict)
        incoming_bundle = BackupBundle.model_validate(migrated_bundle_dict)

        incoming_config = incoming_bundle.config
        if raw_sources:
            incoming_config.sources = raw_sources
        elif getattr(incoming_bundle, "sources", None):
            incoming_config.sources = [Source.model_validate(s) for s in incoming_bundle.sources]
        if raw_epg_sources:
            incoming_config.epg_sources = raw_epg_sources
        elif getattr(incoming_bundle, "epg_sources", None):
            incoming_config.epg_sources = [EPGSource.model_validate(s) for s in incoming_bundle.epg_sources]
        incoming_schedule = incoming_bundle.schedule

        incoming_config = BackupSanitizer.restore_sanitized_fields(incoming_config, existing_config)

        cfg_path = getattr(self.config_handler, "file_path", None)
        sch_path = getattr(self.scheduler_manager, "file_path", None)
        main_db = db_manager.get_main_db_path()

        ts = int(datetime.now(timezone.utc).timestamp())
        cfg_bak: Optional[Path] = None
        sch_bak: Optional[Path] = None
        db_bak: Optional[Path] = None

        if cfg_path and cfg_path.exists():
            cfg_bak = cfg_path.with_suffix(f".bak.{ts}")
            shutil.copy2(cfg_path, cfg_bak)

        if sch_path and sch_path.exists():
            sch_bak = sch_path.with_suffix(f".bak.{ts}")
            shutil.copy2(sch_path, sch_bak)

        if main_db.exists():
            db_bak = main_db.with_suffix(f".bak.{ts}")
            shutil.copy2(main_db, db_bak)

        try:
            incoming_rewrites = (
                getattr(incoming_bundle, "individual_rewrites", None)
                or getattr(incoming_config, "individual_rewrites", None)
                or {}
            )
            if clean_mode == "destructive":
                self.config_handler.save_config(incoming_config)
                self.scheduler_manager.save_config(incoming_schedule.model_dump())
                self._persist_bundle_entities(
                    incoming_bundle, incoming_config, incoming_rewrites, destructive=True
                )
            elif clean_mode == "merge":
                merged_config = self._merge_configs(existing_config, incoming_config)
                merged_schedule = self._merge_schedules(existing_schedule, incoming_schedule.model_dump())
                self.config_handler.save_config(merged_config)
                self.scheduler_manager.save_config(merged_schedule)
                self._persist_bundle_entities(
                    incoming_bundle, incoming_config, incoming_rewrites, destructive=False
                )

            self.scheduler_manager.load_schedule()

            if cfg_bak and cfg_bak.exists():
                cfg_bak.unlink()
            if sch_bak and sch_bak.exists():
                sch_bak.unlink()
            if db_bak and db_bak.exists():
                db_bak.unlink()

            import_result = BackupImportResult(
                success=True,
                mode=clean_mode,
                message=f"Backup bundle imported successfully in '{clean_mode}' mode.",
                snapshot_created=True,
                diff=val_result.diff,
            )

            if trigger_sync:
                try:
                    if self.source_repo.get_active_sources_count() > 0:
                        self.system_service.trigger_update(
                            mode="full",
                            background_tasks=background_tasks,
                            trigger="backup_restore",
                        )
                except Exception as ex:
                    logging.warning(f"Failed to trigger sync after backup restore: {ex}")

            return import_result

        except Exception as e:
            logging.error(f"Import failed during disk persistence: {e}. Initiating rollback...")
            if cfg_bak and cfg_bak.exists() and cfg_path:
                shutil.copy2(cfg_bak, cfg_path)
                cfg_bak.unlink()
            if sch_bak and sch_bak.exists() and sch_path:
                shutil.copy2(sch_bak, sch_path)
                sch_bak.unlink()
            if db_bak and db_bak.exists() and main_db:
                shutil.copy2(db_bak, main_db)
                db_bak.unlink()

            self.scheduler_manager.load_schedule()

            raise InvalidConfigurationError(f"Failed to import backup bundle: {e}. Safety rollback applied.")

    @staticmethod
    def _merge_configs(existing: GlobalConfig, incoming: GlobalConfig) -> GlobalConfig:
        """Merges incoming configuration additively into existing configuration."""
        merged = existing.model_copy(deep=True)

        existing_src_names = {s.name for s in merged.sources}
        for inc_src in incoming.sources:
            if inc_src.name not in existing_src_names:
                merged.sources.append(inc_src)
            else:
                for idx, src in enumerate(merged.sources):
                    if src.name == inc_src.name:
                        merged.sources[idx] = inc_src

        existing_epg_names = {s.name for s in merged.epg_sources}
        for inc_epg in incoming.epg_sources:
            if inc_epg.name not in existing_epg_names:
                merged.epg_sources.append(inc_epg)
            else:
                for idx, epg_src in enumerate(merged.epg_sources):
                    if epg_src.name == inc_epg.name:
                        merged.epg_sources[idx] = inc_epg

        if incoming.individual_rewrites:
            if not merged.individual_rewrites:
                merged.individual_rewrites = {}
            merged.individual_rewrites.update(incoming.individual_rewrites)

        if incoming.channel_merges:
            if not merged.channel_merges:
                merged.channel_merges = {}
            merged.channel_merges.update(incoming.channel_merges)

        if incoming.settings:
            if incoming.settings.user_agent:
                merged.settings.user_agent = incoming.settings.user_agent
            if incoming.settings.epg_retention_days is not None:
                merged.settings.epg_retention_days = incoming.settings.epg_retention_days
            if incoming.settings.search_debounce_ms is not None:
                merged.settings.search_debounce_ms = incoming.settings.search_debounce_ms
            if incoming.settings.force_proxy is not None:
                merged.settings.force_proxy = incoming.settings.force_proxy
            if incoming.settings.rewrites:
                merged.settings.rewrites = incoming.settings.rewrites
            if incoming.settings.notifications and incoming.settings.notifications.enabled:
                merged.settings.notifications = incoming.settings.notifications

        if incoming.auth and incoming.auth.enabled:
            merged.auth = incoming.auth

        return merged

    @staticmethod
    def _merge_schedules(existing_sch: Dict[str, Any], incoming_sch: Dict[str, Any]) -> Dict[str, Any]:
        """Merges incoming scheduled jobs additively into existing schedule."""
        merged = dict(existing_sch)
        merged["enabled"] = incoming_sch.get("enabled", existing_sch.get("enabled", True))

        existing_jobs = list(existing_sch.get("jobs", []))
        incoming_jobs = list(incoming_sch.get("jobs", []))

        existing_job_ids = {j.get("id") for j in existing_jobs if isinstance(j, dict) and j.get("id")}

        for inc_job in incoming_jobs:
            if isinstance(inc_job, dict) and inc_job.get("id"):
                if inc_job["id"] not in existing_job_ids:
                    existing_jobs.append(inc_job)
                else:
                    for idx, j in enumerate(existing_jobs):
                        if isinstance(j, dict) and j.get("id") == inc_job["id"]:
                            existing_jobs[idx] = inc_job

        merged["jobs"] = existing_jobs
        return merged
