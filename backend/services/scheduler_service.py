"""Scheduler service layer encapsulating business logic for background schedule management."""

from typing import Dict, Any, Optional, TYPE_CHECKING

from backend.core.exceptions import InvalidConfigurationError

if TYPE_CHECKING:
    from backend.scheduler.manager import SchedulerManager


class SchedulerService:
    """Service handling background schedule configuration retrieval, available tasks, and updates."""

    def __init__(self, manager: Optional["SchedulerManager"] = None) -> None:
        """Initializes scheduler service with scheduler manager instance.

        Args:
            manager (Optional[SchedulerManager]): Override scheduler manager instance.
        """
        if manager is None:
            from backend.scheduler.manager import scheduler_manager
            self.manager = scheduler_manager
        else:
            self.manager = manager

    @staticmethod
    def get_available_jobs_metadata() -> list:
        """Returns standard metadata list for all registered domain scheduler jobs."""
        from backend.scheduler.jobs.registry import get_available_jobs_metadata
        return get_available_jobs_metadata()

    def get_schedule_config(self) -> Dict[str, Any]:
        """Retrieves background schedule configuration from schedule.yaml with system metadata enrichment.

        Returns:
            Dict[str, Any]: Schedule configuration dictionary.

        Raises:
            HTTPException: 500 Internal Server Error if reading fails.
        """
        try:
            from backend.scheduler.jobs.registry import get_job_class, resolve_canonical_mode

            cfg = self.manager.get_config()
            for job in cfg.get("jobs", []):
                mode = resolve_canonical_mode(job.get("mode", ""))
                job_cls = get_job_class(mode)
                if job_cls:
                    if "is_system" not in job:
                        job["is_system"] = job_cls.is_system
                    if "is_recommended" not in job:
                        job["is_recommended"] = getattr(job_cls, "is_recommended", False)
            return cfg
        except Exception as e:
            raise InvalidConfigurationError(f"Failed to read schedule configuration: {e}")

    def update_schedule_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates schedule configuration in schedule.yaml and synchronizes jobs.

        Args:
            config_data (Dict[str, Any]): Schedule configuration payload dictionary.

        Returns:
            Dict[str, Any]: Updated schedule configuration.

        Raises:
            InvalidConfigurationError: If validation or saving fails.
        """
        try:
            existing_cfg = self.manager.get_config()
            existing_jobs_by_id = {
                j.get("id"): j
                for j in existing_cfg.get("jobs", [])
                if j.get("id")
            }

            incoming_jobs = list(config_data.get("jobs", []))
            incoming_ids = {j.get("id") for j in incoming_jobs if j.get("id")}

            for sys_id, sys_job in existing_jobs_by_id.items():
                if sys_job.get("is_system") and sys_id not in incoming_ids:
                    incoming_jobs.append(dict(sys_job))

            config_data["jobs"] = incoming_jobs

            self.manager.save_config(config_data)
            return self.get_schedule_config()
        except Exception as e:
            raise InvalidConfigurationError(f"Failed to save schedule configuration: {e}")

    def restore_default_jobs(self, mode: str = "missing_only") -> Dict[str, Any]:
        """Restores default system and recommended background scheduled tasks.

        Args:
            mode (str): 'missing_only' or 'full_reset'.

        Returns:
            Dict[str, Any]: Updated schedule configuration.
        """
        try:
            self.manager.restore_default_jobs(mode=mode)
            return self.get_schedule_config()
        except Exception as e:
            raise InvalidConfigurationError(f"Failed to restore default schedule: {e}")
