"""Service managing RFC 8628 Device Authorization pairing with Pluvira Cloud."""

import os
import uuid
import time
import base64
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

from backend.config.settings import settings
from backend.config.models import (
    CloudPairingStartResponse,
    CloudPairingStatusResponse,
    CloudAccountInfo,
)
from backend.core.db import DatabaseManager
from backend.core.exceptions import ValidationDomainError, EntityNotFoundError
from backend.core.backup.crypto import encrypt_packet, decrypt_packet
from backend.core.identity import get_device_hash, reset_instance_identity


class CloudPairingService:
    """Orchestrates RFC 8628 OAuth 2.0 Device Authorization pairing with Pluvira Cloud."""

    _session: Dict[str, Any] = {
        "status": "idle",
        "device_code": None,
        "user_code": None,
        "verification_uri": None,
        "verification_uri_complete": None,
        "expires_at": None,
        "interval": 5.0,
        "uid": None,
        "formatted_id": None,
        "error_message": None,
    }
    _poll_task: Optional[asyncio.Task] = None

    @classmethod
    def get_device_hash(cls) -> str:
        """Resolves or generates a stable SHA-256 device fingerprint."""
        return get_device_hash()

    async def start_pairing(self) -> CloudPairingStartResponse:
        """Initiates RFC 8628 device pairing with Pluvira Cloud.

        Returns:
            CloudPairingStartResponse: Device and user authorization metadata.

        Raises:
            ValidationDomainError: If cloud connection fails or request is rejected.
        """
        self.cancel_pairing()

        device_hash = self.get_device_hash()
        cloud_url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/pairing/device-code"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    cloud_url,
                    json={
                        "device_hash": device_hash,
                        "client_id": "pluvira_core",
                    },
                )
        except Exception as e:
            logging.error(f"Failed to connect to cloud pairing initiation endpoint: {e}")
            raise ValidationDomainError(f"Cloud pairing connection error: {e}")

        if res.status_code != 200:
            err_msg = f"Cloud pairing initiation rejected (HTTP {res.status_code}): {res.text}"
            logging.error(err_msg)
            raise ValidationDomainError(err_msg)

        data = res.json()
        device_code = data.get("device_code", "")
        user_code = data.get("user_code", "")
        verification_uri = data.get("verification_uri", f"{settings.cloud_base_url.rstrip('/')}/portal/pair")
        verification_uri_complete = data.get(
            "verification_uri_complete",
            f"{verification_uri}?code={user_code}",
        )
        expires_in = int(data.get("expires_in", 600))
        interval = float(data.get("interval", 5))

        expires_at = time.time() + expires_in

        CloudPairingService._session = {
            "status": "pending",
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": verification_uri,
            "verification_uri_complete": verification_uri_complete,
            "expires_at": expires_at,
            "interval": interval,
            "uid": None,
            "formatted_id": None,
            "error_message": None,
        }

        CloudPairingService._poll_task = asyncio.create_task(
            self._poll_token_worker(device_code, interval, expires_at)
        )

        return CloudPairingStartResponse(
            device_code=device_code,
            user_code=user_code,
            verification_uri=verification_uri,
            verification_uri_complete=verification_uri_complete,
            expires_in=expires_in,
            interval=int(interval),
        )

    async def _poll_token_worker(self, device_code: str, initial_interval: float, expires_at: float) -> None:
        """Background asynchronous polling worker on Pluvira Cloud /api/v1/pairing/token."""
        token_url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/pairing/token"
        current_interval = max(1.0, initial_interval)

        while time.time() < expires_at:
            if CloudPairingService._session.get("status") != "pending":
                break

            try:
                await asyncio.sleep(current_interval)
            except asyncio.CancelledError:
                break

            if CloudPairingService._session.get("status") != "pending":
                break

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(
                        token_url,
                        json={"device_code": device_code},
                    )
            except Exception as e:
                logging.warning(f"Error querying cloud pairing token: {e}")
                continue

            if res.status_code == 200:
                payload = res.json()
                uid = payload.get("uid") or payload.get("user_id") or ""
                formatted_id = payload.get("formatted_id") or payload.get("formatted_user_id") or uid
                access_token = (
                    payload.get("access_token")
                    or payload.get("token")
                    or payload.get("id_token")
                    or payload.get("bearer_token")
                    or payload.get("jwt")
                )
                license_token = (
                    payload.get("license_token")
                    or payload.get("token_license")
                    or (access_token if (access_token and access_token.startswith("eyJ")) else None)
                )

                device_id = payload.get("device_id")
                device_secret = payload.get("device_secret")
                if device_id and device_secret:
                    self.save_m2m_credentials(
                        device_id=device_id,
                        device_secret=device_secret,
                        uid=uid,
                        formatted_id=formatted_id,
                    )

                DatabaseManager.save_cloud_identity(
                    uid=uid,
                    formatted_id=formatted_id,
                    access_token=access_token,
                    license_token=license_token,
                    device_hash=self.get_device_hash(),
                )

                if license_token:
                    from backend.services.system_service import SystemService
                    try:
                        SystemService().activate_license(license_token)
                    except Exception as err:
                        logging.warning(f"Automatic Pro license activation on pairing failed: {err}")

                CloudPairingService._session["status"] = "success"
                CloudPairingService._session["uid"] = uid
                CloudPairingService._session["formatted_id"] = formatted_id
                CloudPairingService._session["error_message"] = None
                break

            elif res.status_code == 400:
                err_data = res.json()
                detail = err_data.get("detail")
                err_type = detail.get("error") if isinstance(detail, dict) else err_data.get("error")

                if err_type == "authorization_pending":
                    continue
                elif err_type == "slow_down":
                    current_interval += 5.0
                    continue
                elif err_type == "expired_token":
                    CloudPairingService._session["status"] = "expired"
                    CloudPairingService._session["error_message"] = "Pairing session has expired."
                    break
                elif err_type == "access_denied":
                    CloudPairingService._session["status"] = "denied"
                    CloudPairingService._session["error_message"] = "Pairing request was denied by user."
                    break
                else:
                    CloudPairingService._session["status"] = "failed"
                    CloudPairingService._session["error_message"] = f"Pairing error: {err_type or 'unknown'}"
                    break
            else:
                logging.warning(f"Unexpected status code from pairing token endpoint: {res.status_code}")

        if CloudPairingService._session.get("status") == "pending" and time.time() >= expires_at:
            CloudPairingService._session["status"] = "expired"
            CloudPairingService._session["error_message"] = "Pairing session timed out."

    def get_pairing_status(self) -> CloudPairingStatusResponse:
        """Retrieves active device pairing status snapshot."""
        session = CloudPairingService._session
        status = session.get("status", "idle")
        expires_at = session.get("expires_at")

        if status == "pending" and expires_at and time.time() >= expires_at:
            status = "expired"
            session["status"] = "expired"

        return CloudPairingStatusResponse(
            status=status,
            user_code=session.get("user_code"),
            verification_uri_complete=session.get("verification_uri_complete"),
            expires_at=expires_at,
            uid=session.get("uid"),
            formatted_id=session.get("formatted_id"),
            error_message=session.get("error_message"),
        )

    def cancel_pairing(self) -> None:
        """Cancels any active background pairing task and resets session."""
        if CloudPairingService._poll_task and not CloudPairingService._poll_task.done():
            CloudPairingService._poll_task.cancel()
            CloudPairingService._poll_task = None

        CloudPairingService._session = {
            "status": "idle",
            "device_code": None,
            "user_code": None,
            "verification_uri": None,
            "verification_uri_complete": None,
            "expires_at": None,
            "interval": 5.0,
            "uid": None,
            "formatted_id": None,
            "error_message": None,
        }

    def get_cloud_account_info(self) -> CloudAccountInfo:
        """Retrieves linked Pluvira Cloud account record."""
        identity = DatabaseManager.get_cloud_identity()
        if not identity or not identity.get("uid"):
            return CloudAccountInfo(is_linked=False)
        return CloudAccountInfo(
            uid=identity.get("uid"),
            formatted_id=identity.get("formatted_id"),
            access_token=identity.get("access_token"),
            linked_at=identity.get("linked_at"),
            is_linked=True,
        )

    @classmethod
    def get_m2m_credentials(cls) -> Optional[Dict[str, Any]]:
        """Reads M2M device credentials from data/.cloud_pairing.json if present."""
        pairing_file = settings.data_dir / ".cloud_pairing.json"
        if pairing_file.exists() and pairing_file.is_file():
            try:
                import json
                return json.loads(pairing_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    @classmethod
    def save_m2m_credentials(
        cls, device_id: str, device_secret: str, uid: str, formatted_id: str
    ) -> None:
        """Atomically saves M2M device credentials to data/.cloud_pairing.json with 0600 mode."""
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        pairing_file = settings.data_dir / ".cloud_pairing.json"
        import json
        from datetime import datetime, timezone
        data = {
            "device_id": device_id,
            "device_secret": device_secret,
            "uid": uid,
            "formatted_id": formatted_id,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }
        temp_file = pairing_file.with_suffix(f".tmp.{os.getpid()}")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temp_file, 0o600)
        except Exception:
            pass
        os.replace(temp_file, pairing_file)
        try:
            os.chmod(pairing_file, 0o600)
        except Exception:
            pass

    def _resolve_cloud_token(self) -> str:
        """Resolves authentication token or M2M device secret for cloud communication."""
        identity = DatabaseManager.get_cloud_identity()
        m2m = self.get_m2m_credentials()

        uid = (m2m.get("uid") if m2m else None) or (identity.get("uid") if identity else None)
        if not uid:
            raise ValidationDomainError("Cloud account is not linked. Please link your account first.")

        token = None
        if m2m and m2m.get("device_secret"):
            token = m2m.get("device_secret")

        if not token and identity:
            token = identity.get("access_token") or identity.get("license_token")

        if not token:
            cache_file = settings.data_dir / ".license_cache"
            if cache_file.exists():
                try:
                    import json
                    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
                    token = cache_data.get("token")
                except Exception:
                    pass

        if not token:
            raise ValidationDomainError(
                f"Cloud account is linked (UID: {uid}), but authentication credentials (token or device_secret) are missing. Please re-pair your instance."
            )

        return token

    def _get_cloud_request_headers(self, token: str) -> Dict[str, str]:
        """Composes HTTP request headers containing Bearer token and M2M device metadata."""
        identity = DatabaseManager.get_cloud_identity()
        m2m = self.get_m2m_credentials()
        uid = (m2m.get("uid") if m2m else None) or (identity.get("uid") if identity else None)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Device-Hash": self.get_device_hash(),
        }
        if uid:
            headers["X-Pluvira-UID"] = uid
        if m2m and m2m.get("device_id"):
            headers["X-Device-Id"] = m2m["device_id"]
        return headers

    async def list_cloud_snapshots(self) -> list[Dict[str, Any]]:
        """Queries Pluvira Cloud SaaS to retrieve stored E2EE backup snapshots.

        Returns:
            list[Dict[str, Any]]: List of snapshot metadata dictionaries.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/snapshots"
        headers = self._get_cloud_request_headers(token)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=headers)
        except Exception as e:
            logging.error(f"Failed to query cloud backup snapshots: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code != 200:
            raise ValidationDomainError(f"Cloud backup query rejected (HTTP {res.status_code}): {res.text}")

        return res.json()

    async def upload_cloud_snapshot(
        self, encrypted_blob: str, sha256_checksum: str, snapshot_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Uploads client-side encrypted backup blob to Pluvira Cloud E2EE vault.

        Args:
            encrypted_blob (str): Base64 encoded AES-256-GCM ciphertext.
            sha256_checksum (str): Hexadecimal SHA-256 checksum.
            snapshot_label (Optional[str]): Optional user-friendly label.

        Returns:
            Dict[str, Any]: Upload confirmation and metadata.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/upload"
        headers = self._get_cloud_request_headers(token)
        m2m = self.get_m2m_credentials()
        payload = {
            "encrypted_blob_b64": encrypted_blob,
            "encrypted_blob": encrypted_blob,
            "sha256_checksum": sha256_checksum,
            "snapshot_label": snapshot_label or "Manual Cloud Backup",
            "device_hash": self.get_device_hash(),
        }
        if m2m and m2m.get("device_id"):
            payload["device_id"] = m2m["device_id"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers)
        except Exception as e:
            logging.error(f"Failed to upload cloud backup snapshot: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code not in (200, 201):
            raise ValidationDomainError(f"Cloud backup upload rejected (HTTP {res.status_code}): {res.text}")

        return res.json()

    async def download_cloud_snapshot(self, backup_id: str) -> Dict[str, Any]:
        """Downloads an encrypted backup blob from Pluvira Cloud vault.

        Args:
            backup_id (str): Target snapshot identifier.

        Returns:
            Dict[str, Any]: Encrypted blob payload dictionary.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/download/{backup_id}"
        headers = self._get_cloud_request_headers(token)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(url, headers=headers)
        except Exception as e:
            logging.error(f"Failed to download cloud backup snapshot: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code != 200:
            raise ValidationDomainError(f"Cloud backup download rejected (HTTP {res.status_code}): {res.text}")

        try:
            return res.json()
        except Exception:
            return {"id": backup_id, "encrypted_blob": res.text}

    async def download_latest_cloud_snapshot(self) -> Dict[str, Any]:
        """Downloads the latest encrypted backup blob from Pluvira Cloud vault.

        Returns:
            Dict[str, Any]: Encrypted blob payload dictionary for the latest snapshot.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/download/latest"
        headers = self._get_cloud_request_headers(token)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(url, headers=headers)
        except Exception as e:
            logging.error(f"Failed to download latest cloud backup snapshot: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code == 404:
            raise EntityNotFoundError("No backup snapshots found for user.")
        if res.status_code != 200:
            raise ValidationDomainError(f"Cloud backup download latest rejected (HTTP {res.status_code}): {res.text}")

        return res.json()

    async def pin_cloud_snapshot(self, backup_id: str, is_pinned: bool) -> Dict[str, Any]:
        """Updates the pinning state of a cloud backup snapshot.

        Args:
            backup_id (str): Target snapshot identifier.
            is_pinned (bool): Whether the snapshot should be locked.

        Returns:
            Dict[str, Any]: Updated snapshot metadata dictionary.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/{backup_id}/pin"
        headers = self._get_cloud_request_headers(token)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.patch(url, json={"is_pinned": is_pinned}, headers=headers)
        except Exception as e:
            logging.error(f"Failed to pin cloud backup snapshot: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code == 404:
            raise EntityNotFoundError(f"Cloud backup snapshot '{backup_id}' not found.")
        if res.status_code == 403:
            raise ValidationDomainError("Snapshot pinning is only available for Pro and Ultra tiers.")
        if res.status_code == 409:
            raise ValidationDomainError("Cannot pin more than 4 snapshots (at least 1 rotating slot required).")
        if res.status_code != 200:
            raise ValidationDomainError(f"Cloud backup pin request rejected (HTTP {res.status_code}): {res.text}")

        return res.json()

    async def delete_cloud_snapshot(self, backup_id: str) -> None:
        """Deletes a backup snapshot from Pluvira Cloud vault.

        Args:
            backup_id (str): Target snapshot identifier.
        """
        token = self._resolve_cloud_token()
        url = f"{settings.cloud_base_url.rstrip('/')}/api/v1/backup/{backup_id}"
        headers = self._get_cloud_request_headers(token)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.delete(url, headers=headers)
        except Exception as e:
            logging.error(f"Failed to delete cloud backup snapshot: {e}")
            raise ValidationDomainError(f"Cloud connection error: {e}")

        if res.status_code not in (200, 204):
            raise ValidationDomainError(f"Cloud backup deletion rejected (HTTP {res.status_code}): {res.text}")

    @staticmethod
    def encrypt_packet(data_bytes: bytes, passphrase: str) -> tuple[str, str]:
        """Encrypts data bytes with PBKDF2 (600,000 iterations) + AES-256-GCM.

        Args:
            data_bytes (bytes): Plaintext unencrypted binary payload.
            passphrase (str): User private encryption passphrase.

        Returns:
            tuple[str, str]: Base64 encoded ciphertext packet and SHA-256 checksum.
        """
        return encrypt_packet(data_bytes, passphrase)

    @staticmethod
    def decrypt_packet(encrypted_blob: str, passphrase: str) -> bytes:
        """Decrypts Base64 encoded packet using PBKDF2 + AES-256-GCM and decompresses gzip payload.

        Args:
            encrypted_blob (str): Base64 encoded payload packet.
            passphrase (str): User private decryption passphrase.

        Returns:
            bytes: Decrypted and decompressed plaintext bytes.
        """
        return decrypt_packet(encrypted_blob, passphrase)

    async def create_and_upload_cloud_snapshot(
        self, passphrase: str, snapshot_label: Optional[str] = None, pin_snapshot: bool = False
    ) -> Dict[str, Any]:
        """Exports local SQLite backup, encrypts it on local backend, and uploads to cloud vault."""
        if not passphrase or len(passphrase) < 8:
            raise ValidationDomainError("Passphrase must be at least 8 characters long.")

        from backend.services.backup_service import BackupService
        import json

        bundle = BackupService().export_backup(sanitized=False)
        raw_json = json.dumps(bundle.model_dump()).encode("utf-8")

        encrypted_blob, sha256_checksum = self.encrypt_packet(raw_json, passphrase)
        res = await self.upload_cloud_snapshot(
            encrypted_blob=encrypted_blob,
            sha256_checksum=sha256_checksum,
            snapshot_label=snapshot_label or "Manual Cloud Backup",
        )
        if pin_snapshot and res.get("id"):
            try:
                pinned_res = await self.pin_cloud_snapshot(res["id"], True)
                res["is_pinned"] = pinned_res.get("is_pinned", True)
            except Exception as pin_err:
                logging.warning(f"Failed to pin snapshot immediately post-upload: {pin_err}")
        return res

    async def download_latest_and_decrypt_cloud_snapshot(
        self, passphrase: str
    ) -> Dict[str, Any]:
        """Downloads latest encrypted snapshot from cloud vault, decrypts on local backend, and returns bundle dict."""
        if not passphrase:
            raise ValidationDomainError("Decryption passphrase is required.")

        import json

        raw_res = await self.download_latest_cloud_snapshot()
        encrypted_blob = raw_res.get("encrypted_blob_b64") or raw_res.get("encrypted_blob", "")
        if not encrypted_blob:
            raise ValidationDomainError("Downloaded latest cloud snapshot contains empty payload.")

        decompressed_bytes = self.decrypt_packet(encrypted_blob, passphrase)
        try:
            return json.loads(decompressed_bytes.decode("utf-8"))
        except Exception as e:
            raise ValidationDomainError(f"Corrupted backup JSON bundle: {e}")

    async def download_and_decrypt_cloud_snapshot(
        self, backup_id: str, passphrase: str
    ) -> Dict[str, Any]:
        """Downloads encrypted snapshot from cloud vault, decrypts on local backend, and returns bundle dict."""
        if not passphrase:
            raise ValidationDomainError("Decryption passphrase is required.")

        import json

        raw_res = await self.download_cloud_snapshot(backup_id)
        encrypted_blob = raw_res.get("encrypted_blob_b64") or raw_res.get("encrypted_blob", "")
        if not encrypted_blob:
            raise ValidationDomainError("Downloaded cloud snapshot contains empty payload.")

        decompressed_bytes = self.decrypt_packet(encrypted_blob, passphrase)
        try:
            return json.loads(decompressed_bytes.decode("utf-8"))
        except Exception as e:
            raise ValidationDomainError(f"Corrupted backup JSON bundle: {e}")

    def unlink_cloud_account(self) -> None:
        """Unlinks cloud account and wipes stored credentials."""
        self.cancel_pairing()
        DatabaseManager.clear_cloud_identity()
        pairing_file = settings.data_dir / ".cloud_pairing.json"
        if pairing_file.exists():
            try:
                pairing_file.unlink()
            except Exception:
                pass
        reset_instance_identity()
        from backend.services.system_service import SystemService
        SystemService.purge_all_license_caches()
