"""Scheduler job for XMLTV EPG guide synchronization."""

from typing import Any
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.runner import UpdateRunner
from backend.scheduler.jobs.base_job import BaseJob


class EpgSyncGuidesJob(BaseJob):
    """Job that downloads and parses XMLTV guide schedules into database."""

    job_id = "epg_sync_guides"
    display_name = "EPG Guides Sync"
    description = "Downloads and parses XMLTV guide schedules into database with channel mapping resolution."
    is_system = False

    async def run(self, **kwargs: Any) -> Any:
        """Executes EPG guides update run."""
        handler = YAMLConfigHandler()
        config = handler.load_config()
        runner = UpdateRunner(config=config)
        return runner.run(mode="epg", trigger="scheduled")
