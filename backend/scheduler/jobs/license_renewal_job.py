"""System scheduler job for Pro license handshake verification and auto-renewal."""

from typing import Any
from backend.scheduler.jobs.base_job import BaseJob


class LicenseRenewalJob(BaseJob):
    """System job that checks cloud license revocation status and applies auto-renewals."""

    job_id = "license_auto_renewal"
    display_name = "License Sync & Auto-Renewal"
    description = "Periodic cloud synchronization for license feature updates and automated renewals."
    is_system = True

    async def run(self, **kwargs: Any) -> Any:
        """Executes license verification and auto-renewal heartbeat."""
        from backend.services.system_service import SystemService
        return SystemService().check_license_revocation_heartbeat()
