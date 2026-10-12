"""Scheduler jobs package providing modular domain task executors."""

from backend.scheduler.jobs.base_job import BaseJob
from backend.scheduler.jobs.tv_sync_job import TvSyncFullJob, TvSyncChannelsJob
from backend.scheduler.jobs.epg_sync_job import EpgSyncGuidesJob
from backend.scheduler.jobs.stream_health_job import StreamHealthScanJob
from backend.scheduler.jobs.license_renewal_job import LicenseRenewalJob
from backend.scheduler.jobs.cloud_backup_job import CloudBackupJob
from backend.scheduler.jobs.registry import (
    JOB_REGISTRY,
    resolve_canonical_mode,
    get_job_class,
    get_available_jobs_metadata,
)

__all__ = [
    "BaseJob",
    "TvSyncFullJob",
    "TvSyncChannelsJob",
    "EpgSyncGuidesJob",
    "StreamHealthScanJob",
    "LicenseRenewalJob",
    "CloudBackupJob",
    "JOB_REGISTRY",
    "resolve_canonical_mode",
    "get_job_class",
    "get_available_jobs_metadata",
]
