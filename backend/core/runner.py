"""Orchestrator for M3U playlist and XMLTV guide raw acquisition runs persisting to pluvira_epg.db."""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

from backend.config.settings import settings
from backend.config.models import GlobalConfig, Source, EPGSource
from backend.core.file_manager import FileManager
from backend.core.acquisition import PlaylistAcquisitionService, EPGAcquisitionService
from backend.core.raw_database import RawDatabaseService
from backend.core.source_repository import SourceRepository
from backend.core.history import SQLiteHistoryRepository, HistoryRecord, SourceStats, EpgSourceStats
from backend.core.notifier import Notifier
from backend.core.lock_manager import LockManager
from backend.core.system_health import SystemHealth
from backend.core.utils import StreamUtils
from backend.core.update_tracker import update_progress_tracker


class UpdateRunner:
    """Orchestrates download, parsing, and atomic raw persistence for acquisition runs."""

    def __init__(self, config: GlobalConfig) -> None:
        """Initializes runner with configuration.

        Args:
            config (GlobalConfig): Global configuration instance.
        """
        self.config = config
        self.temp_dir = settings.temp_dir
        self.history_repo = SQLiteHistoryRepository()
        self.source_repo = SourceRepository()
        self.db_service = RawDatabaseService()
        self.notifier = Notifier.from_config(config)
        self.lock_manager = LockManager(temp_dir=Path(self.temp_dir))

        self.raw_channels: List[Dict[str, Any]] = []
        self.epg_index: Dict[str, str] = {}
        self.raw_epg: Dict[str, Any] = {}
        self.source_results: Dict[str, Dict[str, Any]] = {}
        self.channels_modified_count: int = 0
        self.turbo_rewrites_duration_s: float = 0.0
        self.is_turbo_rewrites: bool = False

    def run(self, mode: str = "full", target_sources: Optional[List[str]] = None, target_epg_sources: Optional[List[str]] = None, trigger: str = "manual") -> None:
        """Executes raw acquisition run according to mode.

        Args:
            mode (str): Execution mode ('full', 'raw', 'm3u', or 'epg').
            target_sources (Optional[List[str]]): Specific M3U source names to refresh.
            target_epg_sources (Optional[List[str]]): Specific EPG source names to refresh.
        """
        if not self.lock_manager.acquire():
            logging.warning("Acquisition run skipped: another update process is already running.")
            return

        logging.info(f"Starting RAW acquisition run (mode={mode.upper()})...")
        SystemHealth.check_system_health(self.config)
        start_time = time.time()
        self.channels_modified_count = 0
        self.turbo_rewrites_duration_s = 0.0
        self.is_turbo_rewrites = False

        db_sources = self.source_repo.get_all_sources()
        db_epg_sources = self.source_repo.get_all_epg_sources()
        effective_m3u = db_sources if db_sources else self.config.sources
        effective_epg = db_epg_sources if db_epg_sources else getattr(self.config, "epg_sources", [])
        m3u_list = [(s.name, getattr(s, "enabled", True)) for s in effective_m3u]
        epg_list = [(e.name, getattr(e, "enabled", True)) for e in effective_epg]
        update_progress_tracker.reset(mode=mode, m3u_sources=m3u_list, epg_sources=epg_list)

        events = self.config.get_event_config()
        min_ram_mb = events.min_ram_disk_free_mb

        if not FileManager.check_ram_disk_space(Path(self.temp_dir), min_free_mb=min_ram_mb):
            self.notifier.dispatch_event(
                event_name="disk_space_warning",
                title="🔴 Pluvira: RAM Disk Space Low",
                body=f"Low RAM disk storage on '{self.temp_dir}'.",
                severity="critical",
            )

        try:
            if mode == "m3u" or target_sources or target_epg_sources:
                self.epg_index = self.db_service.load_existing_epg_index()
                self.raw_epg = self.db_service.load_existing_raw_epg()
            if mode == "epg" or target_sources or target_epg_sources:
                self.raw_channels = self.db_service.load_existing_channels()
        except Exception as e:
            logging.error(f"Failed to load pre-existing raw databases: {e}")

        try:
            if mode in ["full", "raw", "m3u"]:
                for source in effective_m3u:
                    if not getattr(source, "enabled", True):
                        logging.info(f"Skipping disabled M3U source '{source.name}'.")
                        continue
                    if target_sources and source.name not in target_sources:
                        continue
                    
                    if target_sources:
                        self.raw_channels = [ch for ch in self.raw_channels if ch.get("s") != source.name]
                        
                    self._process_m3u_source(source)

            if mode in ["full", "raw", "epg"]:
                for epg_source in effective_epg:
                    if not getattr(epg_source, "enabled", True):
                        logging.info(f"Skipping disabled EPG source '{epg_source.name}'.")
                        continue
                    if target_epg_sources and epg_source.name not in target_epg_sources:
                        continue
                        
                    if target_epg_sources:
                        prefix = f"{epg_source.name}::"
                        self.epg_index = {k: v for k, v in self.epg_index.items() if not k.startswith(prefix)}
                        self.raw_epg = {k: v for k, v in self.raw_epg.items() if not k.startswith(prefix)}
                        
                    self._process_epg_source(epg_source)

            self._analyze_acquisition_results()
            from backend.core.license_thresholds import LicenseThresholdManager, FREE_TIER_MAX_CHANNELS
            if not LicenseThresholdManager.is_pro_active() and len(self.raw_channels) > FREE_TIER_MAX_CHANNELS:
                logging.warning(
                    f"Free tier limit: capping channels from {len(self.raw_channels)} to {FREE_TIER_MAX_CHANNELS}."
                )
                self.raw_channels = self.raw_channels[:FREE_TIER_MAX_CHANNELS]
            update_progress_tracker.update_phase("database_cache", "running", "Saving database...")
            self.db_service.save_raw_database(self.raw_channels, self.epg_index, self.raw_epg)
            update_progress_tracker.update_phase("database_cache", "success", "Saving completed")

            update_progress_tracker.update_phase("rewrites", "running", "Processing rewrite rules...")
            from backend.core.pro_bridge import ProBridge
            if ProBridge.is_available():
                try:
                    t_rw = time.perf_counter()
                    pro_res = ProBridge.execute_sync(
                        "cascade-rewrite",
                        payload={
                            "command": "cascade-rewrite",
                            "main_db_path": str(settings.data_dir / "pluvira_main.db"),
                            "epg_db_path": str(settings.data_dir / "pluvira_epg.db"),
                            "batch_size": 10000,
                            "options": {
                                "force_proxy_default": bool(getattr(self.config.settings, "force_proxy", False)),
                                "normalize_names": True,
                            },
                        },
                        timeout=60.0,
                    )
                    if pro_res and pro_res.get("status") == "success":
                        self.turbo_rewrites_duration_s = round(time.perf_counter() - t_rw, 3)
                        res_obj = pro_res.get("result", {})
                        if isinstance(res_obj, dict):
                            self.channels_modified_count = res_obj.get("channels_modified", 0)
                        self.is_turbo_rewrites = True
                except Exception as e:
                    logging.warning(f"Pro Turbo cascade rewrite in runner failed: {e}")

            try:
                from backend.core.processor import DataProcessor
                DataProcessor(lock_manager=self.lock_manager).auto_attach_streams_to_personal_channels(config=self.config)
                update_progress_tracker.update_phase("rewrites", "success", "Rewrites completed")
            except Exception as ae:
                logging.warning(f"Auto-attach to personal channels skipped or error: {ae}")
                update_progress_tracker.update_phase("rewrites", "success")

            duration = time.time() - start_time
            logging.info(f"Acquisition run completed in {duration:.2f}s.")
            update_progress_tracker.finish(
                status="success",
                duration=duration,
                total_channels=len(self.raw_channels),
                matched_channels=0,
            )
            self._record_history(mode, duration, "success", trigger=trigger)
            self.notifier.send_success(processed_channels=len(self.raw_channels), elapsed_time=duration)

        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"Acquisition run failed: {e}")
            update_progress_tracker.finish(
                status="failed",
                duration=duration,
                error=str(e),
            )
            self._record_history(mode, duration, "failed", str(e), trigger=trigger)
            self.notifier.send_failure(error_message=str(e))
            raise e
        finally:
            self.lock_manager.release()

    def _process_m3u_source(self, source: Source) -> None:
        """Downloads and parses a single M3U playlist source delegating to PlaylistAcquisitionService.

        Args:
            source (Source): Source configuration object.
        """
        source_ua = source.settings.user_agent if source.settings else ""
        ua = StreamUtils.resolve_user_agent("", source_ua, self.config.settings.user_agent or "")
        update_progress_tracker.start_source(source.name)
        try:
            channels, result = PlaylistAcquisitionService.process_source(
                source=source,
                temp_dir=Path(self.temp_dir),
                global_user_agent=ua,
                notifier=self.notifier,
            )
            self.source_results[source.name] = result
            self.raw_channels.extend(channels)
            if result.get("status") == "success":
                update_progress_tracker.complete_source(source.name, channels=len(channels), duration_s=result.get("duration_s", 0.0))
            else:
                update_progress_tracker.complete_source(source.name, error=result.get("error", "Download failed"), duration_s=result.get("duration_s", 0.0))
        except Exception as e:
            update_progress_tracker.complete_source(source.name, error=str(e))
            raise e

    def _process_epg_source(self, epg_source: EPGSource) -> None:
        """Downloads and parses a single XMLTV guide source delegating to EPGAcquisitionService.

        Args:
            epg_source (EPGSource): EPG guide source configuration object.
        """
        epg_ua = getattr(epg_source, "user_agent", "") or ""
        ua = StreamUtils.resolve_user_agent("", epg_ua, self.config.settings.user_agent or "")
        retention = self.config.settings.epg_retention_days or 7
        update_progress_tracker.start_source(epg_source.name)
        try:
            result = EPGAcquisitionService.process_epg_source(
                epg_source=epg_source,
                temp_dir=Path(self.temp_dir),
                global_user_agent=ua,
                retention_days=retention,
                epg_index=self.epg_index,
                raw_epg=self.raw_epg,
                notifier=self.notifier,
            )
            self.source_results[epg_source.name] = result
            if result.get("status") == "success":
                update_progress_tracker.complete_source(
                    epg_source.name,
                    channels=result.get("count", 0),
                    programmes=result.get("programmes", 0),
                    duration_s=result.get("duration_s", 0.0),
                    engine=result.get("engine", "core"),
                )
            else:
                update_progress_tracker.complete_source(epg_source.name, error=result.get("error", "Download failed"), duration_s=result.get("duration_s", 0.0), engine=result.get("engine", "core"))
        except Exception as e:
            update_progress_tracker.complete_source(epg_source.name, error=str(e))
            raise e

    def _analyze_acquisition_results(self) -> None:
        """Analyzes source acquisition results for partial failure or massive drops."""
        successes = sum(1 for res in self.source_results.values() if res["status"] == "success")
        failures = sum(1 for res in self.source_results.values() if res["status"] != "success")

        if successes > 0 and failures > 0:
            failed_names = [name for name, res in self.source_results.items() if res["status"] != "success"]
            self.notifier.dispatch_event(
                event_name="partial_acquisition",
                title="⚠️ Pluvira: Partial Acquisition",
                body=f"Acquisition completed with mixed results.\nSuccesses: {successes}\nFailures: {failures}\nFailed Sources: {', '.join(failed_names)}",
                severity="warning",
            )

        latest_record = self.history_repo.get_latest()
        if latest_record and latest_record.status == "success" and latest_record.sources_stats:
            prev_counts = {s.source_name: s.channels for s in latest_record.sources_stats}

            events = self.config.get_event_config()
            threshold = events.massive_drop_threshold_pct

            for src_name, res in self.source_results.items():
                if res["type"] == "m3u" and res["status"] == "success":
                    curr_count = res["count"]
                    prev_count = prev_counts.get(src_name, 0)
                    if prev_count > 0 and curr_count < prev_count:
                        drop_pct = ((prev_count - curr_count) / prev_count) * 100.0
                        if drop_pct >= threshold:
                            self.notifier.dispatch_event(
                                event_name="massive_channel_drop",
                                title="⚠️ Pluvira: Massive Channel Drop Detected",
                                body=f"Source '{src_name}' lost {drop_pct:.1f}% of its channels.\nPrevious: {prev_count}\nCurrent: {curr_count}\nThreshold: {threshold}%",
                                severity="warning",
                            )

    def _record_history(self, mode: str, duration: float, status: str, error: str = "", trigger: str = "manual") -> None:
        """Records acquisition execution stats into history repository.

        Args:
            mode (str): Execution mode.
            duration (float): Duration in seconds.
            status (str): Status string ('success' or 'failed').
            error (str): Error message string.
        """
        src_counts: Dict[str, int] = {}
        for ch in self.raw_channels:
            src = ch.get("s", "Unknown")
            src_counts[src] = src_counts.get(src, 0) + 1

        sources_stats = [
            SourceStats(source_name=name, channels=count, matched_epg=0)
            for name, count in src_counts.items()
        ]

        epg_stats = [
            EpgSourceStats(
                source_name=name,
                channels=res.get("count", 0),
                programmes=res.get("programmes", 0),
                duration_s=res.get("duration_s", 0.0),
                engine=res.get("engine", "core"),
            )
            for name, res in self.source_results.items()
            if res.get("type") == "epg"
        ]

        from backend.core.pro_bridge import ProBridge
        self.history_repo.add(HistoryRecord(
            mode=mode,
            duration=round(duration, 2),
            status=status,
            total_channels=len(self.raw_channels),
            matched_channels=0,
            missing_channels=0,
            error_message=error if error else None,
            sources_stats=sources_stats,
            is_turbo=ProBridge.is_available(),
            epg_stats=epg_stats,
            trigger=trigger,
            channels_modified=self.channels_modified_count,
            turbo_rewrites_duration_s=self.turbo_rewrites_duration_s,
            is_turbo_rewrites=self.is_turbo_rewrites,
        ))
