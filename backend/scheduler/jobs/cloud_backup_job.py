"""Scheduler job for automated E2EE cloud backup snapshot synchronization."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from backend.config.settings import settings
from backend.core.db import DatabaseManager
from backend.core.license_thresholds import LicenseThresholdManager
from backend.scheduler.jobs.base_job import BaseJob
from backend.core.backup.crypto import encrypt_packet


class CloudBackupJob(BaseJob):
    """Job that synchronizes E2EE encrypted backup snapshots to Pluvira Cloud vault."""

    job_id: str = "cloud_backup"
    display_name: str = "Cloud Backup Vault Sync"
    description: str = "Automated E2EE cloud backup snapshot synchronization for Pro and Ultra subscribers."
    is_system: bool = False

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Executes automated cloud backup snapshot export, encryption, and upload.

        Returns:
            Dict[str, Any]: Execution status dictionary.
        """
        if not LicenseThresholdManager.is_pro_active():
            logging.info("Cloud backup job skipped: Pro or Ultra license required.")
            return {"status": "skipped", "reason": "pro_required"}

        identity = DatabaseManager.get_cloud_identity()
        if not identity or not identity.get("uid") or not identity.get("access_token"):
            logging.warning("Cloud backup job skipped: Instance is not paired with Pluvira Cloud.")
            return {"status": "skipped", "reason": "not_linked"}

        from backend.services.backup_service import BackupService
        from backend.services.cloud_pairing_service import CloudPairingService

        try:
            secret = settings.storage_secret
            if not secret:
                raise RuntimeError("Storage secret missing for cloud backup.")

            bundle = BackupService().export_backup(sanitized=False)
            raw_bytes = json.dumps(bundle.model_dump()).encode("utf-8")

            b64_blob, checksum = encrypt_packet(raw_bytes, secret)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            label = f"Automated Scheduled Backup ({now_str})"

            res = await CloudPairingService().upload_cloud_snapshot(
                encrypted_blob=b64_blob,
                sha256_checksum=checksum,
                snapshot_label=label,
            )
            return {"status": "success", "snapshot": res}
        except Exception as e:
            err_str = str(e)
            if "409" in err_str:
                logging.warning(f"Automated cloud backup skipped: all slots are pinned: {e}")
                return {"status": "skipped", "reason": "all_slots_pinned"}
            logging.error(f"Automated cloud backup task failed: {e}")
            return {"status": "error", "message": str(e)}
