"""Centralized job registry mapping mode identifiers to job execution classes."""

from typing import Dict, Type, Optional, List, Any
from backend.scheduler.jobs.base_job import BaseJob
from backend.scheduler.jobs.tv_sync_job import TvSyncFullJob, TvSyncChannelsJob
from backend.scheduler.jobs.epg_sync_job import EpgSyncGuidesJob
from backend.scheduler.jobs.stream_health_job import StreamHealthScanJob
from backend.scheduler.jobs.license_renewal_job import LicenseRenewalJob
from backend.scheduler.jobs.cloud_backup_job import CloudBackupJob

TvSyncFullJob.is_recommended = True
EpgSyncGuidesJob.is_recommended = True
CloudBackupJob.is_recommended = True
StreamHealthScanJob.is_recommended = True

JOB_REGISTRY: Dict[str, Type[BaseJob]] = {
    TvSyncFullJob.job_id: TvSyncFullJob,
    TvSyncChannelsJob.job_id: TvSyncChannelsJob,
    EpgSyncGuidesJob.job_id: EpgSyncGuidesJob,
    StreamHealthScanJob.job_id: StreamHealthScanJob,
    LicenseRenewalJob.job_id: LicenseRenewalJob,
    CloudBackupJob.job_id: CloudBackupJob,
}

SYSTEM_DEFAULT_JOBS: List[Dict[str, Any]] = [
    {
        "id": "license_auto_renewal",
        "enabled": True,
        "trigger": "interval",
        "hours": 0,
        "minutes": 2,
        "mode": "license_auto_renewal",
        "description": "Periodic license synchronization and auto-renewal heartbeat",
        "is_system": True,
        "is_recommended": False,
    },
    {
        "id": "pluvira_update_daily",
        "enabled": True,
        "trigger": "cron",
        "hour": 4,
        "minute": 0,
        "day_of_week": "*",
        "mode": "tv_sync_full",
        "description": "Run daily full TV and EPG sync at 4:00 AM UTC",
        "is_system": False,
        "is_recommended": True,
    },
    {
        "id": "epg_update_frequent",
        "enabled": True,
        "trigger": "cron",
        "hour": "*/6",
        "minute": 30,
        "day_of_week": "*",
        "mode": "epg_sync_guides",
        "description": "Refresh XMLTV guide programmes every 6 hours",
        "is_system": False,
        "is_recommended": True,
    },
    {
        "id": "cloud_backup_weekly",
        "enabled": True,
        "trigger": "cron",
        "day_of_week": "0",
        "hour": 3,
        "minute": 0,
        "mode": "cloud_backup",
        "description": "Automated E2EE cloud backup snapshot synchronization for Pro and Ultra subscribers.",
        "is_system": False,
        "is_recommended": True,
    },
]

LEGACY_MODE_ALIASES: Dict[str, str] = {
    "full": TvSyncFullJob.job_id,
    "m3u": TvSyncChannelsJob.job_id,
    "raw": TvSyncFullJob.job_id,
    "epg": EpgSyncGuidesJob.job_id,
    "link_test": StreamHealthScanJob.job_id,
    "license_heartbeat": LicenseRenewalJob.job_id,
    "license_revocation_heartbeat": LicenseRenewalJob.job_id,
    "backup_cloud": CloudBackupJob.job_id,
    "cloud_backup_vault": CloudBackupJob.job_id,
}


def resolve_canonical_mode(mode: str) -> str:
    """Resolves legacy mode strings into canonical domain-driven identifiers.

    Args:
        mode (str): Input mode string.

    Returns:
        str: Canonical mode identifier.
    """
    clean = (mode or "").strip().lower()
    return LEGACY_MODE_ALIASES.get(clean, clean)


def get_job_class(mode: str) -> Optional[Type[BaseJob]]:
    """Resolves concrete BaseJob class for a given execution mode with legacy fallback.

    Args:
        mode (str): Canonical or legacy mode identifier.

    Returns:
        Optional[Type[BaseJob]]: Matched job class or None.
    """
    canonical = resolve_canonical_mode(mode)
    return JOB_REGISTRY.get(canonical)


def get_available_jobs_metadata() -> List[Dict[str, Any]]:
    """Returns metadata list for all registered domain scheduler jobs.

    Returns:
        List[Dict[str, Any]]: Ordered list of job metadata dictionaries.
    """
    metadata_list = []
    for job_cls in JOB_REGISTRY.values():
        meta = job_cls.get_metadata()
        meta["is_recommended"] = getattr(job_cls, "is_recommended", False)
        metadata_list.append(meta)
    return metadata_list
