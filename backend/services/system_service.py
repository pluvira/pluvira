"""System service layer encapsulating business logic for system status, acquisition execution, logs, and cache."""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import BackgroundTasks

from backend.config.settings import settings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.exceptions import ValidationDomainError, ProcessLockedError
from backend.core.file_manager import FileManager
from backend.core.runner import UpdateRunner
from backend.utils.logger import consume_logs_from_queue
from backend.core.pro_bridge import ProBridge
from backend.core.update_tracker import update_progress_tracker
from backend.core.version import get_environment_info


class SystemService:
    """Service handling system execution state, update task triggering, logs, and cache operations."""

    _system_state: Dict[str, Any] = {
        "is_running": False,
        "current_mode": "idle",
    }

    def __init__(self, config_handler: Optional[YAMLConfigHandler] = None) -> None:
        """Initializes system service.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()

    def get_status(self) -> Dict[str, Any]:
        """Retrieves current execution status of the system.

        Returns:
            Dict[str, Any]: Dictionary with execution state, status string, and edition details.
        """
        is_running = self._system_state["is_running"]
        edition_info = ProBridge.get_edition_info(force_refresh=True)
        from backend.core.db import DatabaseManager
        cloud_id = DatabaseManager.get_cloud_identity()
        crockford_id = cloud_id.get("uid") if cloud_id else None
        cloud_account_linked = bool(cloud_id)

        license_dict = edition_info.get("license")
        pro_ver = edition_info.get("pro_version") or (license_dict.get("pro_version") if isinstance(license_dict, dict) else None)
        if not pro_ver and edition_info.get("pro_active"):
            env_ver = os.getenv("PLUVIRA_PRO_VERSION") or os.getenv("PLUVIRA_VERSION")
            if env_ver:
                pro_ver = env_ver.lstrip("v")
        if isinstance(license_dict, dict):
            license_dict["crockford_id"] = crockford_id
            license_dict["cloud_account_linked"] = cloud_account_linked

        from backend.core.identity import get_device_hash
        dev_hash = get_device_hash(data_dir=settings.data_dir)

        webrtc_active = False
        webrtc_status = "disabled"
        if cloud_account_linked and not edition_info.get("pro_active"):
            if edition_info.get("tier") in ("core", None):
                edition_info["tier"] = "free"
                if not edition_info.get("display_name_full") or edition_info.get("display_name_full") == "Pluvira Core":
                    edition_info["display_name_full"] = "Free Registered"
                if not edition_info.get("compact_name") or edition_info.get("compact_name") == "CORE":
                    edition_info["compact_name"] = "FREE"
                if not edition_info.get("badge_icon") or edition_info.get("badge_icon") == "sparkles":
                    edition_info["badge_icon"] = "user-check"
                if not edition_info.get("badge_color"):
                    edition_info["badge_color"] = "#0ea5e9"
                if not edition_info.get("badge_text_color"):
                    edition_info["badge_text_color"] = "#ffffff"
        if edition_info.get("pro_active"):
            modules = (license_dict.get("modules") or []) if isinstance(license_dict, dict) else []
            if "webrtc_remote" in modules or "webrtc" in modules:
                webrtc_status = "standby"

        return {
            "is_running": is_running,
            "status": "Running" if is_running else "Idle",
            "mode": self._system_state["current_mode"],
            "edition": edition_info["edition"],
            "tier": edition_info.get("tier", "core"),
            "display_name_full": edition_info.get("display_name_full"),
            "compact_name": edition_info.get("compact_name"),
            "badge_icon": edition_info.get("badge_icon", "sparkles"),
            "badge_color": edition_info.get("badge_color"),
            "badge_text_color": edition_info.get("badge_text_color"),
            "max_ips": edition_info.get("max_ips", 2),
            "max_slots": edition_info.get("max_slots", 2),
            "backup_max_slots": edition_info.get("backup_max_slots", 0),
            "pro_active": edition_info["pro_active"],
            "license_valid": edition_info["license_valid"],
            "pro_version": pro_ver,
            "update_recommended": edition_info.get("update_recommended", False),
            "supported_commands": edition_info.get("supported_commands", []),
            "supported_modules": edition_info.get("supported_modules", []),
            "crockford_id": crockford_id,
            "cloud_account_linked": cloud_account_linked,
            "device_hash": dev_hash,
            "webrtc_active": webrtc_active,
            "webrtc_status": webrtc_status,
            "license": license_dict,
            "edition_message": edition_info["message"],
            "cloud_endpoints": settings.cloud_endpoints,
            "environment": get_environment_info(),
        }

    def claim_trial_license(self, token: Optional[str] = None, cloud_url: Optional[str] = None) -> Dict[str, Any]:
        """Activates or updates 14-day on-demand Pro trial license.

        Args:
            token (Optional[str]): Signed Ed25519 trial token.
            cloud_url (Optional[str]): Optional cloud URL override for trial claiming.

        Returns:
            Dict[str, Any]: Updated license details dictionary.
        """
        trial_token = token
        if not trial_token:
            base_url = (cloud_url or os.getenv("PLUVIRA_CLOUD_URL", settings.cloud_base_url)).rstrip("/")
            endpoint = f"{base_url}/api/v1/license/trial"
            import httpx
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(endpoint, json={})
                    if res.status_code == 200:
                        trial_token = res.json().get("token")
                    elif res.status_code == 403:
                        from backend.core.exceptions import LicenseThresholdExceededError
                        raise LicenseThresholdExceededError("Trial already claimed or exhausted.")
            except httpx.RequestError as e:
                logging.warning(f"Could not connect to cloud trial endpoint: {e}")

        if trial_token:
            cache_path = settings.data_dir / ".license_cache"
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            temp_file = cache_path.with_suffix(f".tmp.{os.getpid()}")
            temp_file.write_text(trial_token.strip(), encoding="utf-8")
            FileManager.atomic_write(temp_file, cache_path)

        ProBridge.invalidate_cache()
        return self.get_license_info()

    def activate_license(self, token: str) -> Dict[str, Any]:
        """Activates and validates a commercial Pro license token.

        Args:
            token (str): Signed Ed25519 JWT license token.

        Returns:
            Dict[str, Any]: Structured activation response containing success, message, license, and error_code.

        Raises:
            ValidationDomainError: If token string is empty or invalid format.
        """
        clean_token = token.strip() if token else ""
        if not clean_token:
            raise ValidationDomainError("License token cannot be empty.")

        if re.match(r"^[0-9a-fA-F-]{36}$", clean_token):
            return {
                "success": False,
                "message": "You entered a License Key (UUID). Please paste the cryptographic Ed25519 Token (starts with 'eyJhbGciOi...').",
                "license": None,
                "error_code": "LICENSE_KEY_INSERTED_INSTEAD_OF_TOKEN",
            }

        ProBridge.invalidate_cache()
        license_res = ProBridge.verify_license(token=clean_token, save_cache=True)
        is_valid = license_res.get("valid", False)

        if is_valid:
            ProBridge.invalidate_cache()
            return {
                "success": True,
                "message": "Commercial Pro license activated successfully.",
                "license": license_res,
                "error_code": None,
            }
        else:
            err_code = license_res.get("error_code") or "LICENSE_INVALID"
            msg = license_res.get("message") or "License token verification failed."
            return {
                "success": False,
                "message": f"License activation failed: {msg}",
                "license": license_res,
                "error_code": err_code,
            }

    @staticmethod
    def read_license_cache() -> Dict[str, Any]:
        """Reads and deserializes local .license_cache file safely."""
        cache_file = settings.data_dir / ".license_cache"
        if cache_file.exists() and cache_file.is_file():
            try:
                raw = cache_file.read_text(encoding="utf-8").strip()
                if not raw:
                    return {}
                if raw.startswith("{"):
                    return json.loads(raw)
                return {"token": raw}
            except Exception:
                return {}
        return {}

    @classmethod
    def purge_all_license_caches(cls) -> None:
        """Public entrypoint to purge .license_cache across data_dir and local root paths."""
        cls._purge_all_license_caches()

    @staticmethod
    def _purge_all_license_caches() -> None:
        """Purges .license_cache across data_dir and local root paths."""
        candidate_paths = [
            settings.data_dir / ".license_cache",
            Path(".license_cache"),
            Path("./data/.license_cache"),
        ]
        for p in candidate_paths:
            try:
                if p.exists() and p.is_file():
                    p.unlink()
            except Exception:
                pass
        ProBridge.invalidate_cache()

    def _purge_revoked_license(self, cloud_id: Optional[Dict[str, Any]], auth_token: Optional[str] = None) -> None:
        """Purges local license cache and resets cloud identity license token on revocation."""
        from backend.core.db import DatabaseManager
        self._purge_all_license_caches()
        if cloud_id and cloud_id.get("uid"):
            DatabaseManager.save_cloud_identity(
                uid=cloud_id["uid"],
                formatted_id=cloud_id.get("formatted_id", ""),
                access_token=cloud_id.get("access_token") or auth_token,
                license_token=None,
                device_hash=cloud_id.get("device_hash"),
            )
        logging.warning("LICENSE_REVOKED_BY_SAAS: No active license in cloud portal. Local Pro license cache purged.")

    def sync_cloud_license(self) -> Dict[str, Any]:
        """Fetches active license from Pluvira Cloud customer portal and activates it locally.

        Returns:
            Dict[str, Any]: Structured license activation response.
        """
        from backend.core.db import DatabaseManager
        from backend.services.cloud_pairing_service import CloudPairingService
        cloud_id = DatabaseManager.get_cloud_identity()
        m2m_creds = CloudPairingService.get_m2m_credentials()
        if not cloud_id or not cloud_id.get("uid"):
            return {
                "success": False,
                "message": "Cloud account is not linked. Please link your account via RFC 8628 pairing first.",
                "detail": "Cloud account is not linked. Please link your account via RFC 8628 pairing first.",
                "license": None,
                "code": "CLOUD_ACCOUNT_NOT_LINKED",
                "error_code": "CLOUD_ACCOUNT_NOT_LINKED",
            }

        if m2m_creds and m2m_creds.get("device_id") and m2m_creds.get("device_secret"):
            cloud_base_url = settings.cloud_base_url.rstrip("/")
            url = f"{cloud_base_url}/api/v1/pairing/sync-license"
            headers = {
                "Authorization": f"Bearer {m2m_creds['device_secret']}",
                "Content-Type": "application/json",
            }
            from backend.core.version import get_version
            app_ver = get_version()
            edition_info = ProBridge.get_edition_info()
            pro_ver = edition_info.get("pro_version") or None

            target_triplet = os.getenv("PLUVIRA_TARGET_TRIPLET")
            ipc_contract_ver = 1
            if ProBridge.is_binary_installed():
                try:
                    ping_res = ProBridge.execute_sync("ping", payload={}, timeout=2.0)
                    if ping_res and isinstance(ping_res, dict):
                        p_res = ping_res.get("result")
                        if isinstance(p_res, dict):
                            if not pro_ver:
                                pro_ver = p_res.get("version") or p_res.get("pro_version")
                            target_triplet = target_triplet or p_res.get("build_target") or p_res.get("target_triplet")
                            if "ipc_contract_version" in p_res:
                                try:
                                    ipc_contract_ver = int(p_res["ipc_contract_version"])
                                except (ValueError, TypeError):
                                    pass
                except Exception:
                    pass

            if not target_triplet:
                import platform
                machine = platform.machine().lower()
                sys_name = platform.system().lower()
                if sys_name == "linux":
                    target_triplet = f"{machine}-unknown-linux-gnu"
                elif sys_name == "darwin":
                    target_triplet = f"{machine}-apple-darwin"
                else:
                    target_triplet = f"{machine}-pc-windows-msvc"

            deployment_type = os.getenv("PLUVIRA_DEPLOYMENT_TYPE", "docker")

            body = {
                "device_id": m2m_creds["device_id"],
                "device_hash": CloudPairingService.get_device_hash(),
                "app_version": app_ver,
                "pro_version": pro_ver,
                "target_triplet": target_triplet,
                "deployment_type": deployment_type,
                "ipc_contract_version": ipc_contract_ver,
            }
            import httpx
            try:
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(url, headers=headers, json=body)
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("has_license") and data.get("license_token"):
                            raw_tok = str(data["license_token"]).strip()
                            act_res = self.activate_license(raw_tok)
                            if act_res.get("success"):
                                DatabaseManager.save_cloud_identity(
                                    uid=cloud_id["uid"],
                                    formatted_id=cloud_id.get("formatted_id", ""),
                                    access_token=cloud_id.get("access_token"),
                                    license_token=raw_tok,
                                    device_hash=cloud_id.get("device_hash"),
                                )
                                tier_info = data.get("tier_info") if isinstance(data.get("tier_info"), dict) else (data.get("tier_metadata") if isinstance(data.get("tier_metadata"), dict) else {})
                                meta_dict = {
                                    "tier": tier_info.get("id") or tier_info.get("slug") or data.get("tier"),
                                    "display_name_full": tier_info.get("display_name_full") or data.get("display_name_full"),
                                    "compact_name": tier_info.get("name") or tier_info.get("compact_name") or data.get("compact_name"),
                                    "badge_icon": tier_info.get("badge_icon") or data.get("badge_icon"),
                                    "badge_color": tier_info.get("badge_color") or data.get("badge_color"),
                                    "badge_text_color": tier_info.get("badge_text_color") or data.get("badge_text_color"),
                                    "max_ips": tier_info.get("default_max_ips") or data.get("default_max_ips") or data.get("max_ips"),
                                    "max_slots": data.get("max_slots"),
                                    "backup_max_slots": tier_info.get("backup_max_slots") or data.get("backup_max_slots"),
                                }
                                cache_file = settings.data_dir / ".license_cache"
                                cache_payload = self.read_license_cache()
                                cache_payload["token"] = raw_tok
                                for k, v in meta_dict.items():
                                    if v is not None:
                                        cache_payload[k] = v
                                        if isinstance(act_res.get("license"), dict):
                                            act_res["license"][k] = v
                                cache_payload["last_online_handshake_utc"] = int(datetime.now(timezone.utc).timestamp())
                                cache_payload["last_online_status"] = "ok"
                                temp_file = cache_file.with_suffix(f".tmp.{os.getpid()}")
                                temp_file.write_text(json.dumps(cache_payload), encoding="utf-8")
                                FileManager.atomic_write(temp_file, cache_file)
                                ProBridge.invalidate_cache()
                                act_res["message"] = "Pro/Ultra license synchronized and activated successfully from Pluvira Cloud."
                            return act_res
                        else:
                            self._purge_revoked_license(cloud_id)
                            tier_info = data.get("tier_info") if isinstance(data.get("tier_info"), dict) else (data.get("tier_metadata") if isinstance(data.get("tier_metadata"), dict) else {})
                            free_meta = {
                                "version": 1,
                                "token": "",
                                "device_hash": CloudPairingService.get_device_hash(),
                                "tier": "free",
                                "display_name_full": tier_info.get("display_name_full") or data.get("display_name_full") or "Free Registered",
                                "compact_name": tier_info.get("name") or tier_info.get("compact_name") or data.get("compact_name") or "FREE",
                                "badge_icon": tier_info.get("badge_icon") or data.get("badge_icon") or "user-check",
                                "badge_color": tier_info.get("badge_color") or data.get("badge_color") or "#0ea5e9",
                                "badge_text_color": tier_info.get("badge_text_color") or data.get("badge_text_color") or "#ffffff",
                                "max_ips": tier_info.get("default_max_ips") or data.get("default_max_ips") or data.get("max_ips", 2),
                                "max_slots": data.get("max_slots", 2),
                                "backup_max_slots": tier_info.get("backup_max_slots") or data.get("backup_max_slots", 1),
                                "last_online_handshake_utc": int(datetime.now(timezone.utc).timestamp()),
                                "last_online_status": "ok",
                            }
                            cache_file = settings.data_dir / ".license_cache"
                            temp_file = cache_file.with_suffix(f".tmp.{os.getpid()}")
                            temp_file.write_text(json.dumps(free_meta), encoding="utf-8")
                            FileManager.atomic_write(temp_file, cache_file)
                            ProBridge.invalidate_cache()
                            return {
                                "success": False,
                                "message": data.get("message") or "No active Pro licenses found for this account.",
                                "detail": data.get("message") or "No active Pro licenses found for this account.",
                                "license": None,
                                "code": "NO_ACTIVE_LICENSE_FOUND",
                                "error_code": "NO_ACTIVE_LICENSE_FOUND",
                            }
                    elif res.status_code == 403:
                        CloudPairingService().unlink_cloud_account()
                        return {
                            "success": False,
                            "message": "Device authorization was revoked from the cloud portal. Please repeat pairing.",
                            "detail": "Device authorization was revoked from the cloud portal. Please repeat pairing.",
                            "license": None,
                            "code": "DEVICE_REVOKED",
                            "error_code": "DEVICE_REVOKED",
                        }
                    elif res.status_code == 401:
                        return {
                            "success": False,
                            "message": "Device authorization secret rejected by cloud. Please repeat pairing.",
                            "detail": "Device authorization secret rejected by cloud. Please repeat pairing.",
                            "license": None,
                            "code": "INVALID_DEVICE_SECRET",
                            "error_code": "INVALID_DEVICE_SECRET",
                        }
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "message": f"Could not connect to Pluvira Cloud M2M sync: {e}",
                    "license": None,
                    "error_code": "CLOUD_UNREACHABLE",
                }

        auth_token = cloud_id.get("access_token") or cloud_id.get("license_token")
        if not auth_token:
            cache_payload = self.read_license_cache()
            auth_token = cache_payload.get("token")

        if not auth_token:
            return {
                "success": False,
                "message": "Cloud authentication token is missing or expired. Please repeat RFC 8628 device pairing.",
                "detail": "Cloud authentication token is missing or expired. Please repeat RFC 8628 device pairing.",
                "license": None,
                "code": "CLOUD_AUTH_EXPIRED",
                "error_code": "CLOUD_AUTH_EXPIRED",
            }

        cloud_base_url = settings.cloud_base_url.rstrip("/")
        url = f"{cloud_base_url}/api/v1/portal/licenses"
        headers = {"Authorization": f"Bearer {auth_token}"}

        import httpx
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code in (401, 403):
                    return {
                        "success": False,
                        "message": "Cloud authentication token expired or rejected. Please repeat RFC 8628 device pairing.",
                        "detail": "Cloud authentication token expired or rejected. Please repeat RFC 8628 device pairing.",
                        "license": None,
                        "error_code": "CLOUD_AUTH_EXPIRED",
                    }
                elif res.status_code != 200:
                    return {
                        "success": False,
                        "message": f"Cloud returned HTTP {res.status_code}: {res.text}",
                        "license": None,
                        "error_code": "CLOUD_SYNC_FAILED",
                    }
                licenses_data = res.json()
        except httpx.RequestError as e:
            return {
                "success": False,
                "message": f"Could not connect to Pluvira Cloud portal: {e}",
                "license": None,
                "error_code": "CLOUD_UNREACHABLE",
            }

        if isinstance(licenses_data, list):
            items = licenses_data
        elif isinstance(licenses_data, dict):
            items = licenses_data.get("licenses") or licenses_data.get("items") or licenses_data.get("data") or []
        else:
            items = []

        if not items:
            self._purge_revoked_license(cloud_id, auth_token)
            return {
                "success": False,
                "message": "No active Pro/Ultra licenses found in your Pluvira Cloud account. Local license downgraded.",
                "detail": "No active Pro/Ultra licenses found in your Pluvira Cloud account. Local license downgraded.",
                "code": "NO_ACTIVE_LICENSE_FOUND",
                "license": None,
                "error_code": "NO_ACTIVE_LICENSE_FOUND",
            }

        acceptable_statuses = {"active", "issued", "valid", "pending", "pending_activation", "trial", ""}
        candidate_licenses = [
            lic for lic in items
            if isinstance(lic, dict)
            and lic.get("token")
            and str(lic.get("status", "")).strip().lower() in acceptable_statuses
        ]

        if candidate_licenses:
            candidate_licenses.sort(
                key=lambda x: (
                    str(x.get("status", "")).strip().lower() in ("active", "issued", "valid"),
                    float(x.get("expires_at") or 0),
                ),
                reverse=True,
            )
            target_lic = candidate_licenses[0]
        else:
            token_items = [lic for lic in items if isinstance(lic, dict) and lic.get("token")]
            target_lic = token_items[0] if token_items else (items[0] if items else None)
        raw_token = target_lic.get("token") if isinstance(target_lic, dict) else None

        if not raw_token:
            return {
                "success": False,
                "message": "Found license record in cloud portal but cryptographic Ed25519 token is missing.",
                "license": None,
                "error_code": "LICENSE_TOKEN_MISSING",
            }

        activation_result = self.activate_license(raw_token)
        if activation_result.get("success"):
            DatabaseManager.save_cloud_identity(
                uid=cloud_id["uid"],
                formatted_id=cloud_id.get("formatted_id", ""),
                access_token=cloud_id.get("access_token") or auth_token,
                license_token=raw_token.strip(),
                device_hash=cloud_id.get("device_hash"),
            )
            if isinstance(target_lic, dict):
                cache_file = settings.data_dir / ".license_cache"
                cache_payload = self.read_license_cache()
                cache_payload["token"] = raw_token.strip()
                for meta_key in ("tier", "display_name_full", "compact_name", "badge_icon", "badge_color", "badge_text_color", "max_ips", "max_slots", "backup_max_slots"):
                    val = target_lic.get(meta_key)
                    if val is not None:
                        cache_payload[meta_key] = val
                        if isinstance(activation_result.get("license"), dict):
                            activation_result["license"][meta_key] = val
                temp_file = cache_file.with_suffix(f".tmp.{os.getpid()}")
                temp_file.write_text(json.dumps(cache_payload), encoding="utf-8")
                FileManager.atomic_write(temp_file, cache_file)
                ProBridge.invalidate_cache()
            activation_result["message"] = "Pro/Ultra license synchronized and activated successfully from Pluvira Cloud."
        return activation_result

    def check_license_revocation_heartbeat(self) -> Dict[str, Any]:
        """Periodically verifies license validity on Pluvira Cloud and triggers silent renewal or revocation."""
        import json
        from backend.core.db import DatabaseManager
        cloud_id = DatabaseManager.get_cloud_identity()
        if not cloud_id or not cloud_id.get("uid"):
            return {"status": "skipped", "reason": "unpaired"}

        cache_file = settings.data_dir / ".license_cache"
        cache_payload = self.read_license_cache()
        token = cache_payload.get("token")
        if not token and cloud_id and cloud_id.get("license_token"):
            token = cloud_id.get("license_token")
            cache_payload = {"token": token}

        if not token:
            return {"status": "skipped", "reason": "no_token"}

        import httpx
        from datetime import datetime, timezone
        known_hash = self.get_known_bulletin_hash()
        hb_payload: Dict[str, Any] = {"token": token}
        if known_hash:
            hb_payload["known_bulletin_hash"] = known_hash

        from backend.core.bulletin_repository import BulletinRepository
        bulletin_repo = BulletinRepository()
        pending_acks = bulletin_repo.get_pending_events()
        has_acks = bool(pending_acks.received or pending_acks.read or pending_acks.dismissed)
        if has_acks:
            hb_payload["acked_bulletins"] = pending_acks.model_dump()

        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    f"{settings.cloud_base_url.rstrip('/')}/api/v1/license/heartbeat",
                    json=hb_payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "revoked" or data.get("valid") is False:
                    self._purge_revoked_license(cloud_id)
                    logging.warning("License heartbeat detected revocation. Local edition downgraded to Core.")
                    return {"status": "revoked", "error_code": "NO_ACTIVE_LICENSE_FOUND"}
                cache_payload["last_online_handshake_utc"] = int(datetime.now(timezone.utc).timestamp())
                cache_payload["last_online_status"] = "ok"

                if has_acks:
                    bulletin_repo.pop_and_drain_events(pending_acks)

                if "bulletin_hash" in data and data["bulletin_hash"]:
                    self.set_known_bulletin_hash(data["bulletin_hash"])

                raw_bulletins = data.get("bulletins")
                if raw_bulletins and isinstance(raw_bulletins, list):
                    from backend.config.models import BulletinDTO
                    dto_list = []
                    for b_dict in raw_bulletins:
                        try:
                            dto_list.append(BulletinDTO(**b_dict))
                        except Exception as parse_err:
                            logging.warning(f"Failed parsing incoming bulletin: {parse_err}")
                    if dto_list:
                        bulletin_repo.upsert_bulletins(dto_list)
                    bulletin_repo.prune_expired()

                tier_info = data.get("tier_info") if isinstance(data.get("tier_info"), dict) else (data.get("tier_metadata") if isinstance(data.get("tier_metadata"), dict) else {})
                for k, src_val in [
                    ("tier", tier_info.get("id") or tier_info.get("slug") or data.get("tier")),
                    ("display_name_full", tier_info.get("display_name_full") or data.get("display_name_full")),
                    ("compact_name", tier_info.get("name") or tier_info.get("compact_name") or data.get("compact_name")),
                    ("badge_icon", tier_info.get("badge_icon") or data.get("badge_icon")),
                    ("badge_color", tier_info.get("badge_color") or data.get("badge_color")),
                    ("badge_text_color", tier_info.get("badge_text_color") or data.get("badge_text_color")),
                    ("max_ips", tier_info.get("default_max_ips") or data.get("default_max_ips") or data.get("max_ips")),
                    ("max_slots", tier_info.get("max_slots") or data.get("max_slots")),
                    ("backup_max_slots", tier_info.get("backup_max_slots") or data.get("backup_max_slots")),
                ]:
                    if src_val is not None:
                        cache_payload[k] = src_val

                if data.get("updated_token"):
                    cache_payload["token"] = data["updated_token"]
                    if cloud_id and cloud_id.get("uid"):
                        DatabaseManager.save_cloud_identity(
                            uid=cloud_id["uid"],
                            formatted_id=cloud_id.get("formatted_id", ""),
                            access_token=cloud_id.get("access_token"),
                            license_token=data["updated_token"],
                            device_hash=cloud_id.get("device_hash"),
                        )

                settings.data_dir.mkdir(parents=True, exist_ok=True)
                temp_file = cache_file.with_suffix(f".tmp.{os.getpid()}")
                temp_file.write_text(json.dumps(cache_payload), encoding="utf-8")
                FileManager.atomic_write(temp_file, cache_file)
                
                ProBridge.invalidate_cache()
                logging.info("License heartbeat verified successfully.")
                return {"status": "active", "license": {"valid": True, "license_status": "valid"}}

            elif resp.status_code in (401, 403):
                data = resp.json()
                if data.get("status") == "revoked" or data.get("valid") is False:
                    self._purge_revoked_license(cloud_id)
                    logging.warning("License heartbeat detected revocation. Local edition downgraded to Core.")
                    return {"status": "revoked", "error_code": "NO_ACTIVE_LICENSE_FOUND"}
                return {"status": "error", "error_code": "AUTH_ERROR"}

        except (httpx.ConnectError, httpx.TimeoutException):
            # Cloud unreachable: Do NOT purge cache. Pro binary enforces 48h offline window.
            return {"status": "error", "error_code": "CLOUD_UNREACHABLE"}
        except Exception as e:
            logging.error(f"Heartbeat error: {e}")
            return {"status": "error", "error_code": "UNKNOWN_ERROR"}
        
        return {"status": "error", "error_code": "UNKNOWN_ERROR"}

    def get_license_info(self, force_online: bool = False) -> Dict[str, Any]:
        """Retrieves detailed Pro license lifecycle and module entitlement metadata.

        Returns:
            Dict[str, Any]: License details dictionary.
        """
        if force_online:
            from backend.core.db import DatabaseManager
            from backend.services.cloud_pairing_service import CloudPairingService
            cloud_id = DatabaseManager.get_cloud_identity()
            m2m_creds = CloudPairingService.get_m2m_credentials()
            if cloud_id and cloud_id.get("uid") and m2m_creds and m2m_creds.get("device_id") and m2m_creds.get("device_secret"):
                self.sync_cloud_license()
            else:
                hb = self.check_license_revocation_heartbeat()
                if hb.get("status") == "revoked":
                    ProBridge.invalidate_cache()

        info = ProBridge.get_edition_info(force_refresh=True)
        from backend.core.db import DatabaseManager
        cloud_id = DatabaseManager.get_cloud_identity()
        crockford_id = cloud_id.get("uid") if cloud_id else None
        cloud_account_linked = bool(cloud_id)
        info["crockford_id"] = crockford_id
        info["cloud_account_linked"] = cloud_account_linked
        if cloud_account_linked and not info.get("pro_active"):
            if info.get("tier") in ("core", None):
                info["tier"] = "free"
                if not info.get("display_name_full") or info.get("display_name_full") == "Pluvira Core":
                    info["display_name_full"] = "Free Registered"
                if not info.get("compact_name") or info.get("compact_name") == "CORE":
                    info["compact_name"] = "FREE"
                if not info.get("badge_icon") or info.get("badge_icon") == "sparkles":
                    info["badge_icon"] = "user-check"
                if not info.get("badge_color"):
                    info["badge_color"] = "#0ea5e9"
                if not info.get("badge_text_color"):
                    info["badge_text_color"] = "#ffffff"
        lic = info.get("license")
        if isinstance(lic, dict):
            lic["crockford_id"] = crockford_id
            lic["cloud_account_linked"] = cloud_account_linked
            if not info.get("pro_version") and lic.get("pro_version"):
                info["pro_version"] = lic.get("pro_version")
            if not info.get("tier") and lic.get("tier"):
                info["tier"] = lic.get("tier")
            if not info.get("display_name_full") and lic.get("display_name_full"):
                info["display_name_full"] = lic.get("display_name_full")
            if not info.get("badge_icon") and lic.get("badge_icon"):
                info["badge_icon"] = lic.get("badge_icon")
            if not info.get("compact_name") and lic.get("compact_name"):
                info["compact_name"] = lic.get("compact_name")
            if not info.get("badge_color") and lic.get("badge_color"):
                info["badge_color"] = lic.get("badge_color")
            if not info.get("badge_text_color") and lic.get("badge_text_color"):
                info["badge_text_color"] = lic.get("badge_text_color")
            if not info.get("max_ips") and lic.get("max_ips"):
                info["max_ips"] = lic.get("max_ips")
            if not info.get("max_slots") and lic.get("max_slots"):
                info["max_slots"] = lic.get("max_slots")
            if not info.get("backup_max_slots") and lic.get("backup_max_slots"):
                info["backup_max_slots"] = lic.get("backup_max_slots")
        return info

    def is_running(self) -> bool:
        """Checks if a system update task is currently running.

        Returns:
            bool: True if running, False otherwise.
        """
        return bool(self._system_state["is_running"])

    def set_running_state(self, is_running: bool, mode: str = "idle") -> None:
        """Sets system execution running state and mode.

        Args:
            is_running (bool): Running state boolean.
            mode (str): Execution mode string.
        """
        SystemService._system_state["is_running"] = is_running
        SystemService._system_state["current_mode"] = mode

    def trigger_update(self, mode: str, background_tasks: BackgroundTasks, trigger: str = "manual") -> Dict[str, str]:
        """Triggers background acquisition and update process.

        Args:
            mode (str): Execution mode ('full', 'raw', 'm3u', or 'epg').
            background_tasks (BackgroundTasks): FastAPI background tasks dependency.

        Returns:
            Dict[str, str]: Status message.

        Raises:
            HTTPException: 400 Bad Request if mode is invalid, or 423 Locked if already running.
        """
        if mode not in ["full", "raw", "m3u", "epg"]:
            raise ValidationDomainError("Invalid mode. Must be 'full', 'raw', 'm3u', or 'epg'.")

        if self.is_running():
            raise ProcessLockedError("System update process is already running.")

        background_tasks.add_task(self.run_acquisition_task, mode, trigger)
        return {"message": f"System acquisition task started in mode '{mode}'."}

    def run_acquisition_task(self, mode: str, trigger: str = "manual") -> None:
        """Executes acquisition update runner task in background thread.

        Args:
            mode (str): Execution mode ('full', 'raw', 'm3u', or 'epg').
        """
        self.set_running_state(True, mode)
        try:
            config = self.config_handler.load_config()
            runner = UpdateRunner(config=config)
            runner.run(mode=mode, trigger=trigger)
            logging.info(f"Background acquisition task executed successfully (mode={mode}).")
        except Exception as e:
            logging.error(f"Background acquisition task failed: {e}")
        finally:
            self.set_running_state(False, "idle")

    def run_selective_refresh_task(self, mode: str, source_names: List[str]) -> None:
        """Executes selective M3U or EPG source refresh in background thread.

        Args:
            mode (str): Refresh mode ('m3u' or 'epg').
            source_names (List[str]): List of target source names.
        """
        self.set_running_state(True, f"{mode}_selective")
        try:
            config = self.config_handler.load_config()
            from backend.core.runner import UpdateRunner
            runner = UpdateRunner(config=config)
            if mode == "m3u":
                runner.run(mode="m3u", target_sources=source_names, trigger="manual")
            else:
                runner.run(mode="epg", target_epg_sources=source_names, trigger="manual")
            logging.info(f"Selective {mode.upper()} refresh completed for sources: {source_names}")
        except Exception as e:
            logging.error(f"Selective {mode.upper()} refresh failed: {e}")
        finally:
            self.set_running_state(False, "idle")

    def get_logs(self, max_items: int = 100) -> List[str]:
        """Retrieves recent execution runtime logs from real-time queue.

        Args:
            max_items (int): Max log lines to consume.

        Returns:
            List[str]: List of log message strings.
        """
        return consume_logs_from_queue(max_items=max_items)

    def get_update_progress(self) -> Dict[str, Any]:
        """Retrieves point-in-time snapshot of the update progress tracker.

        Returns:
            Dict[str, Any]: Progress DTO model dump.
        """
        return update_progress_tracker.get_snapshot().model_dump()

    def clear_cache(self) -> Dict[str, str]:
        """Clears in-memory processed channel caches and temporary RAM storage.

        Returns:
            Dict[str, str]: Operation status message.
        """
        try:
            from backend.core.artwork_cache import ArtworkCache
            ArtworkCache().clear()
        except Exception:
            pass
        return {"message": "System cache cleared successfully."}

    def factory_reset(self) -> Dict[str, Any]:
        """Performs full system factory reset restoring configs and databases to initial state.

        Returns:
            Dict[str, Any]: Operation success status and message.
        """
        from backend.core.lock_manager import LockManager
        lock_mgr = LockManager()
        if not lock_mgr.acquire():
            raise ProcessLockedError("System update process is already running.")

        try:
            from ruamel.yaml import YAML
            from backend.config.defaults import get_default_config_yaml
            from backend.core.file_manager import FileManager
            from backend.scheduler.manager import scheduler_manager

            yaml = YAML()
            yaml.preserve_quotes = True
            default_config = get_default_config_yaml()
            temp_config = settings.config_path.with_suffix(f".reset.{os.getpid()}")
            with open(temp_config, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f)
            FileManager.atomic_write(temp_config, settings.config_path)

            scheduler_manager._create_default_schedule()
            scheduler_manager.load_schedule()

            from backend.core.db import db_manager, DatabaseManager
            from backend.core.link_status import link_status_repo
            from backend.core.history import SQLiteHistoryRepository
            from backend.services.playlist_service import PlaylistService
            from backend.core.processor import DataProcessor
            from backend.core.artwork_cache import ArtworkCache

            for db_path in [
                settings.data_dir / "pluvira_main.db",
                settings.data_dir / "pluvira_epg.db",
                settings.data_dir / "pluvira_metadata.db",
            ]:
                if db_path.exists():
                    conn = db_manager.get_connection(db_path)
                    with conn:
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                        for (tbl,) in cursor.fetchall():
                            try:
                                conn.execute(f"DELETE FROM {tbl};")
                            except Exception:
                                pass

            DatabaseManager.clear_cloud_identity()
            from backend.core.identity import reset_instance_identity
            reset_instance_identity(settings.data_dir)
            pairing_file = settings.data_dir / ".cloud_pairing.json"
            if pairing_file.exists():
                try:
                    pairing_file.unlink()
                except Exception:
                    pass

            PlaylistService().ensure_default_playlist()
            from backend.config.defaults import get_default_global_rules
            from backend.core.metadata_rule_repository import MetadataRuleRepository
            MetadataRuleRepository(db_path=settings.data_dir / "pluvira_main.db").set_global_rules(get_default_global_rules())

            link_status_repo.reset_all()
            SQLiteHistoryRepository().clear_all()
            try:
                ArtworkCache().clear()
            except Exception:
                pass

            self._purge_all_license_caches()
            ProBridge.invalidate_cache()

            if settings.temp_dir.exists():
                for item in settings.temp_dir.iterdir():
                    if item != lock_mgr.lock_file:
                        try:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                import shutil
                                shutil.rmtree(item, ignore_errors=True)
                        except Exception:
                            pass

            return {
                "success": True,
                "message": "Factory reset completed successfully. All data and settings restored to factory defaults.",
            }
        finally:
            lock_mgr.release()

    @classmethod
    def get_known_bulletin_hash(cls) -> Optional[str]:
        """Reads memoized known bulletin hash from data storage."""
        hash_file = settings.data_dir / ".bulletin_hash"
        if hash_file.exists():
            try:
                return hash_file.read_text(encoding="utf-8").strip() or None
            except Exception:
                return None
        return None

    @classmethod
    def set_known_bulletin_hash(cls, hash_val: Optional[str]) -> None:
        """Persists known bulletin hash to data storage."""
        if not hash_val:
            return
        hash_file = settings.data_dir / ".bulletin_hash"
        try:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            temp_file = hash_file.with_suffix(f".tmp.{os.getpid()}")
            temp_file.write_text(hash_val.strip(), encoding="utf-8")
            FileManager.atomic_write(temp_file, hash_file)
        except Exception as e:
            logging.warning(f"Failed to persist bulletin hash: {e}")

    def get_active_bulletins(self, include_dismissed: bool = False) -> List[Any]:
        """Retrieves active bulletins from BulletinRepository."""
        from backend.core.bulletin_repository import BulletinRepository
        return BulletinRepository().get_active_bulletins(include_dismissed=include_dismissed)

    def dismiss_bulletin(self, bulletin_id: str) -> bool:
        """Dismisses a bulletin in BulletinRepository."""
        from backend.core.bulletin_repository import BulletinRepository
        return BulletinRepository().dismiss_bulletin(bulletin_id)

    def mark_bulletin_read(self, bulletin_id: str) -> bool:
        """Marks a bulletin as read in BulletinRepository."""
        from backend.core.bulletin_repository import BulletinRepository
        return BulletinRepository().mark_read(bulletin_id)

    def delete_bulletin(self, bulletin_id: str) -> bool:
        """Deletes a bulletin in BulletinRepository."""
        from backend.core.bulletin_repository import BulletinRepository
        return BulletinRepository().delete_bulletin(bulletin_id)

    def clear_archived_bulletins(self) -> int:
        """Clears all archived/dismissed bulletins in BulletinRepository."""
        from backend.core.bulletin_repository import BulletinRepository
        return BulletinRepository().clear_archived_bulletins()
