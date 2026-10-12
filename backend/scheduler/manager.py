"""Background task scheduler manager using APScheduler."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import timezone
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config.settings import settings
from backend.core.lock_manager import LockManager
from backend.core.notifier import Notifier
from backend.core.file_manager import FileManager
from backend.scheduler.jobs.registry import get_job_class, resolve_canonical_mode


class SchedulerManager:
    """Manages APScheduler lifecycle and schedule.yaml persistence."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        """Initializes scheduler manager.

        Args:
            file_path (Optional[Path]): Override path to schedule.yaml.
        """
        self.file_path = file_path or settings.schedule_path
        self.scheduler = AsyncIOScheduler(timezone=timezone.utc)
        self.yaml = YAML()
        self.yaml.preserve_quotes = True

    def start(self) -> None:
        """Starts the background scheduler if not running."""
        if not self.scheduler.running:
            self.scheduler.start()
            logging.info("APScheduler started successfully.")

    def shutdown(self) -> None:
        """Shuts down the background scheduler if running."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logging.info("APScheduler shut down successfully.")

    def get_config(self) -> Dict[str, Any]:
        """Reads schedule.yaml configuration as a dictionary.

        Returns:
            Dict[str, Any]: Schedule configuration dictionary.
        """
        if not self.file_path.exists():
            self._create_default_schedule()
        with open(self.file_path, "r", encoding="utf-8") as f:
            return self.yaml.load(f) or {}

    def save_config(self, config_data: Dict[str, Any]) -> None:
        """Saves configuration data to schedule.yaml and syncs scheduler jobs.

        Args:
            config_data (Dict[str, Any]): Updated schedule configuration.
        """
        data = self.get_config()
        data["enabled"] = config_data.get("enabled", True)

        jobs_seq = CommentedSeq()
        for job in config_data.get("jobs", []):
            job_map = CommentedMap()
            job_map["id"] = job.get("id", "unnamed_job")
            job_map["enabled"] = bool(job.get("enabled", True))
            trigger_type = job.get("trigger", "cron")
            job_map["trigger"] = trigger_type
            raw_mode = job.get("mode", "tv_sync_full")
            canonical_mode = resolve_canonical_mode(raw_mode)
            job_map["mode"] = canonical_mode

            job_cls = get_job_class(canonical_mode)
            is_sys = bool(job.get("is_system", job_cls.is_system if job_cls else False))
            job_map["is_system"] = is_sys
            job_map["is_recommended"] = bool(job.get("is_recommended", False))

            if trigger_type == "cron":
                job_map["hour"] = job.get("hour", 4)
                job_map["minute"] = job.get("minute", 0)
                if "day_of_week" in job:
                    job_map["day_of_week"] = job["day_of_week"]
            elif trigger_type == "interval":
                job_map["hours"] = job.get("hours", 0)
                job_map["minutes"] = job.get("minutes", 0)

            if "link_test_filters" in job:
                job_map["link_test_filters"] = job["link_test_filters"]
            if "description" in job:
                job_map["description"] = job["description"]
            jobs_seq.append(job_map)

        data["jobs"] = jobs_seq

        temp_file = self.file_path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                self.yaml.dump(data, f)
            FileManager.atomic_write(temp_file, self.file_path)
            self._sync_jobs(data)
            logging.info("Schedule configuration saved and jobs synchronized.")
        except Exception as e:
            logging.error(f"Failed to save schedule.yaml: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def load_schedule(self) -> None:
        """Loads schedule configuration and synchronizes jobs."""
        data = self.get_config()
        self._sync_jobs(data)

    def restore_default_jobs(self, mode: str = "missing_only") -> Dict[str, Any]:
        """Restores default system and recommended jobs.

        Args:
            mode (str): 'missing_only' to inject absent factory jobs, 'full_reset' to overwrite defaults.

        Returns:
            Dict[str, Any]: Updated schedule configuration.
        """
        from backend.scheduler.jobs.registry import SYSTEM_DEFAULT_JOBS

        config = self.get_config()
        existing_jobs = list(config.get("jobs", []))

        if mode == "full_reset":
            default_ids = {j["id"] for j in SYSTEM_DEFAULT_JOBS}
            custom_jobs = [j for j in existing_jobs if j.get("id") not in default_ids]
            new_jobs = [dict(j) for j in SYSTEM_DEFAULT_JOBS] + custom_jobs
            config["jobs"] = new_jobs
        else:
            existing_ids = {j.get("id") for j in existing_jobs if j.get("id")}
            for default_job in SYSTEM_DEFAULT_JOBS:
                if default_job["id"] not in existing_ids:
                    existing_jobs.append(dict(default_job))
            config["jobs"] = existing_jobs

        self.save_config(config)
        return self.get_config()

    def _sync_jobs(self, config: Dict[str, Any]) -> None:
        """Resets and registers jobs in APScheduler from config.

        Args:
            config (Dict[str, Any]): Schedule configuration dictionary.
        """
        self.scheduler.remove_all_jobs()

        if not config.get("enabled", True):
            logging.info("Scheduler disabled in configuration.")
            return

        for job_dict in config.get("jobs", []):
            job_id = job_dict.get("id")
            if not job_id or not job_dict.get("enabled", True):
                continue

            trigger_type = job_dict.get("trigger", "cron")
            try:
                if trigger_type == "cron":
                    trigger = CronTrigger(
                        hour=job_dict.get("hour"),
                        minute=job_dict.get("minute"),
                        day_of_week=job_dict.get("day_of_week"),
                        timezone=timezone.utc,
                    )
                elif trigger_type == "interval":
                    trigger = IntervalTrigger(
                        hours=job_dict.get("hours", 0),
                        minutes=job_dict.get("minutes", 0),
                        timezone=timezone.utc,
                    )
                else:
                    continue

                self.scheduler.add_job(
                    func=SchedulerManager._scheduled_update_task,
                    trigger=trigger,
                    id=job_id,
                    kwargs={
                        "mode": job_dict.get("mode", "full"),
                        "link_test_filters": job_dict.get("link_test_filters"),
                        "job_id": job_id,
                    },
                    replace_existing=True,
                )
                logging.info(f"Scheduled job '{job_id}' (trigger={trigger_type}, mode={job_dict.get('mode', 'full')}).")
            except Exception as e:
                logging.error(f"Failed to schedule job '{job_id}': {e}")

    @staticmethod
    async def _scheduled_update_task(
        mode: str = "full",
        link_test_filters: Optional[Dict[str, Any]] = None,
        job_id: str = "manual",
    ) -> None:
        """Task callback executed by APScheduler to run acquisition or link testing.

        Args:
            mode (str): Execution mode string ('full', 'raw', 'm3u', 'epg', or 'link_test').
            link_test_filters (Optional[Dict[str, Any]]): Filters for link test scanner mode.
            job_id (str): Identifier of scheduled job.
        """
        lock_mgr = LockManager()
        if lock_mgr.is_locked():
            logging.warning(f"Scheduled job '{job_id}' skipped: system lock is active.")
            try:
                notifier = Notifier.from_config()
                notifier.dispatch_event(
                    event_name="scheduled_job_skipped",
                    title="⚠️ Pluvira: Scheduled Job Skipped",
                    body=f"Job '{job_id}' ({mode.upper()}) was skipped because system lock is active.",
                    severity="warning",
                )
            except Exception as e:
                logging.error(f"Failed to dispatch scheduled_job_skipped notification: {e}")
            return

        try:
            job_cls = get_job_class(mode)
            if not job_cls:
                logging.error(f"Unrecognized scheduled job mode '{mode}' for job '{job_id}'.")
                return

            job_instance = job_cls()
            await job_instance.run(link_test_filters=link_test_filters, job_id=job_id)
        except Exception as e:
            logging.error(f"Scheduled update task '{job_id}' failed: {e}")

    def _create_default_schedule(self) -> None:
        """Creates default schedule.yaml if file does not exist."""
        os.makedirs(self.file_path.parent, exist_ok=True)
        default_yaml = CommentedMap()
        default_yaml["enabled"] = True

        jobs_seq = CommentedSeq()
        job = CommentedMap()
        job["id"] = "pluvira_update_daily"
        job["enabled"] = True
        job["trigger"] = "cron"
        job["hour"] = 4
        job["minute"] = 0
        job["mode"] = "tv_sync_full"
        job["description"] = "Run daily full update at 4:00 AM UTC"
        job["is_system"] = False
        jobs_seq.append(job)

        job_heartbeat = CommentedMap()
        job_heartbeat["id"] = "license_auto_renewal"
        job_heartbeat["enabled"] = True
        job_heartbeat["trigger"] = "interval"
        job_heartbeat["hours"] = 0
        job_heartbeat["minutes"] = 2
        job_heartbeat["mode"] = "license_auto_renewal"
        job_heartbeat["description"] = "Periodic license synchronization and auto-renewal heartbeat"
        job_heartbeat["is_system"] = True
        jobs_seq.append(job_heartbeat)

        default_yaml["jobs"] = jobs_seq
        with open(self.file_path, "w", encoding="utf-8") as f:
            self.yaml.dump(default_yaml, f)


scheduler_manager = SchedulerManager()
