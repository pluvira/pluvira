"""Scheduler job for automated stream link verification and health ranking."""

from typing import Any, Dict, Optional
from backend.core.processor import DataProcessor
from backend.core.scanner import run_link_test_batch_task
from backend.scheduler.jobs.base_job import BaseJob


class StreamHealthScanJob(BaseJob):
    """Job that runs background polite link verification for filtered streams."""

    job_id = "stream_health_scan"
    display_name = "Stream Link Health Scan"
    description = "Executes background polite link testing to verify stream reachability and compute health scores."
    is_system = False

    async def run(self, link_test_filters: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        """Executes batch link testing."""
        processor = DataProcessor()
        channels_to_test = processor.get_channels_for_link_test(link_test_filters or {})
        items = [
            {
                "url": ch["url"],
                "original_url": ch["original_url"],
                "source": ch["source"],
                "user_agent": ch.get("user_agent", ""),
            }
            for ch in channels_to_test
        ]
        if items:
            return await run_link_test_batch_task(items)
        return {"scanned": 0, "online": 0, "offline": 0}
