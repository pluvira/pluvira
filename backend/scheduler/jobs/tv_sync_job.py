"""Scheduler jobs for IPTV playlist synchronization and end-to-end updates."""

from typing import Any
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.runner import UpdateRunner
from backend.scheduler.jobs.base_job import BaseJob


class TvSyncFullJob(BaseJob):
    """Job that executes full end-to-end update (channels, EPG guides, and cache generation)."""

    job_id = "tv_sync_full"
    display_name = "Full TV & EPG Sync"
    description = "Complete synchronization of M3U playlist channels, XMLTV guide programmes, and cache generation."
    is_system = False

    async def run(self, **kwargs: Any) -> Any:
        """Executes full update run."""
        handler = YAMLConfigHandler()
        config = handler.load_config()
        runner = UpdateRunner(config=config)
        return runner.run(mode="full", trigger="scheduled")


class TvSyncChannelsJob(BaseJob):
    """Job that downloads and parses M3U playlist channels only."""

    job_id = "tv_sync_channels"
    display_name = "Channels Playlist Sync"
    description = "Downloads and parses M3U playlist channels with allow/deny filters and metadata rewrites."
    is_system = False

    async def run(self, **kwargs: Any) -> Any:
        """Executes channels playlist update run."""
        handler = YAMLConfigHandler()
        config = handler.load_config()
        runner = UpdateRunner(config=config)
        return runner.run(mode="m3u", trigger="scheduled")
