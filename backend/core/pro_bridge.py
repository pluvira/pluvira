"""Bridge service for executing proprietary Pro Rust binaries via Subprocess IPC."""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.config.settings import settings


class ProBridge:
    """Handles async subprocess IPC execution with Rust Pro binary."""

    _edition_cache: Optional[Dict[str, Any]] = None
    _edition_cache_time: float = 0.0
    _CACHE_TTL: float = 60.0

    @classmethod
    def _get_cached_token(cls) -> Optional[str]:
        """Retrieves the active cached license JWT token from local disk storage."""
        for cache_path in [
            settings.data_dir / ".license_cache",
            Path("data/.license_cache"),
            Path(".license_cache"),
        ]:
            if cache_path.exists() and cache_path.is_file():
                try:
                    content = cache_path.read_text(encoding="utf-8").strip()
                    if content.startswith("{"):
                        data = json.loads(content)
                        tok = data.get("token")
                        if tok and isinstance(tok, str) and tok.strip():
                            return tok.strip()
                    elif content:
                        return content
                except Exception:
                    pass
        return None

    @staticmethod
    def _extract_jwt_claims(token: Optional[str]) -> Dict[str, Any]:
        """Safely extracts unverified claims dictionary from JWT Base64URL payload."""
        if not token or not isinstance(token, str):
            return {}
        try:
            import base64
            parts = token.strip().split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                decoded = base64.urlsafe_b64decode(payload_b64)
                claims = json.loads(decoded.decode("utf-8", errors="replace"))
                if isinstance(claims, dict):
                    return claims
        except Exception:
            pass
        return {}

    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidates the in-memory edition and license status cache."""
        cls._edition_cache = None
        cls._edition_cache_time = 0.0

    @classmethod
    def get_edition_info(
        cls, force_refresh: bool = False, custom_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Inspects and returns runtime edition information, pinging Pro binary and verifying license.

        Args:
            force_refresh (bool): Force re-evaluation ignoring memory cache.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Dict[str, Any]: Edition details payload.
        """
        import time
        now = time.time()
        if not force_refresh and cls._edition_cache and (now - cls._edition_cache_time < cls._CACHE_TTL):
            return cls._edition_cache

        if not cls.is_binary_installed(custom_path):
            info = {
                "edition": "core",
                "tier": "core",
                "display_name_full": "Pluvira Core",
                "compact_name": "CORE",
                "badge_icon": "sparkles",
                "badge_color": None,
                "badge_text_color": None,
                "max_ips": 2,
                "max_slots": 2,
                "backup_max_slots": 0,
                "pro_binary_found": False,
                "pro_active": False,
                "license_valid": False,
                "pro_version": None,
                "update_recommended": False,
                "supported_commands": [],
                "supported_modules": [],
                "message": "Pro binary not found. Running in standard Pluvira Core edition.",
            }
            cls._edition_cache = info
            cls._edition_cache_time = now
            return info

        license_res = cls.verify_license(custom_path)
        is_valid = license_res.get("valid", False)

        pro_ver = license_res.get("pro_version")
        supported_commands: List[str] = []
        supported_modules: List[str] = []
        if cls.is_binary_installed(custom_path):
            try:
                ping_res = cls.execute_sync("ping", payload={}, timeout=2.0, custom_path=custom_path)
                if ping_res and isinstance(ping_res, dict):
                    p_res = ping_res.get("result")
                    if isinstance(p_res, dict):
                        if not pro_ver:
                            pro_ver = p_res.get("pro_version") or p_res.get("version")
                        supported_commands = p_res.get("supported_commands") or []
                        supported_modules = p_res.get("supported_modules") or []
            except Exception:
                pass
        if not pro_ver and is_valid:
            env_ver = os.getenv("PLUVIRA_PRO_VERSION") or os.getenv("PLUVIRA_VERSION")
            if env_ver:
                pro_ver = env_ver.lstrip("v")

        if is_valid:
            lic_status = license_res.get("license_status", "valid")
            days_left = license_res.get("days_remaining")

            if lic_status == "expiring_soon":
                logging.warning(
                    f"⚠️ Pro license is expiring soon! ({days_left} day(s) remaining until expiration)."
                )
            elif lic_status == "grace_period":
                logging.warning(
                    "⚠️ Backend offline: Internet connection lost. Pluvira Pro running in offline mode (active for up to 48h). Restore internet connection to re-enable cloud sync."
                )

            if lic_status == "grace_period":
                status_msg = "Pro binary active in Offline Mode (Internet connection required. Active offline for up to 48h)."
            else:
                status_msg = f"Pro binary active (Status: {lic_status.upper()}, Days left: {days_left})."

            info = {
                "edition": "pro",
                "tier": license_res.get("tier", "pro"),
                "display_name_full": license_res.get("display_name_full") or "Pluvira Pro",
                "compact_name": license_res.get("compact_name") or "PRO",
                "badge_icon": license_res.get("badge_icon", "sparkles"),
                "badge_color": license_res.get("badge_color"),
                "badge_text_color": license_res.get("badge_text_color"),
                "max_ips": license_res.get("max_ips", 20),
                "max_slots": license_res.get("max_slots", 7),
                "backup_max_slots": license_res.get("backup_max_slots", 5),
                "pro_binary_found": True,
                "pro_active": True,
                "license_valid": True,
                "license": license_res,
                "pro_version": pro_ver,
                "update_recommended": license_res.get("update_recommended", False),
                "supported_commands": supported_commands,
                "supported_modules": supported_modules,
                "message": status_msg,
            }
        else:
            err_code = license_res.get("error_code") or "LICENSE_INVALID"
            reason = license_res.get("message") or err_code
            if license_res.get("compatible") is False:
                msg = f"Pro binary found but version incompatible or yanked ({reason}). Falling back to Core edition."
            else:
                msg = f"Pro binary found but license inactive ({err_code}: {reason}). Falling back to Core edition."
            info = {
                "edition": "core",
                "tier": license_res.get("tier", "core"),
                "display_name_full": license_res.get("display_name_full") or "Pluvira Core",
                "compact_name": license_res.get("compact_name") or "CORE",
                "badge_icon": license_res.get("badge_icon", "sparkles"),
                "badge_color": license_res.get("badge_color"),
                "badge_text_color": license_res.get("badge_text_color"),
                "max_ips": 2,
                "max_slots": 2,
                "backup_max_slots": 0,
                "pro_binary_found": True,
                "pro_active": False,
                "license_valid": False,
                "license": license_res,
                "pro_version": pro_ver,
                "update_recommended": license_res.get("update_recommended", False),
                "supported_commands": supported_commands,
                "supported_modules": supported_modules,
                "message": msg,
            }

        cls._edition_cache = info
        cls._edition_cache_time = now
        return info

    @classmethod
    def verify_license(
        cls,
        custom_path: Optional[Path] = None,
        token: Optional[str] = None,
        save_cache: bool = True,
    ) -> Dict[str, Any]:
        """Executes license verification command via Subprocess IPC.

        Args:
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Dict[str, Any]: Standardized license verification dictionary.
        """
        from backend import __version__
        from backend.core.identity import get_device_hash
        payload = {
            "client_metadata": {
                "app_version": __version__,
                "core_version": __version__,
                "ipc_contract_version": 1,
                "device_hash": get_device_hash(),
                "deployment_type": os.getenv("PLUVIRA_DEPLOYMENT_TYPE", "docker"),
            }
        }
        cached_meta: Dict[str, Any] = {}
        if token and token.strip():
            payload["items"] = [token.strip()]
        else:
            cache_file = settings.data_dir / ".license_cache"
            if not cache_file.exists() and Path("data/.license_cache").exists():
                cache_file = Path("data/.license_cache")
            if cache_file.exists():
                try:
                    cached_data = cache_file.read_text(encoding="utf-8").strip()
                    if cached_data.startswith("{"):
                        import json
                        parsed = json.loads(cached_data)
                        cached_token = parsed.get("token")
                        if isinstance(parsed, dict):
                            cached_meta = parsed
                    else:
                        cached_token = cached_data
                    if cached_token:
                        payload["items"] = [cached_token]
                except Exception:
                    pass

        raw_res = cls.execute_sync("verify-license", payload=payload, timeout=5.0, custom_path=custom_path)
        if not raw_res:
            raw_res = cls.execute_sync("validate-license", payload=payload, timeout=5.0, custom_path=custom_path)

        if not isinstance(raw_res, dict):
            return {
                "valid": False,
                "status": "error",
                "error_code": "IPC_UNAVAILABLE",
                "message": "Pro binary IPC communication failed",
                "license_status": "unlicensed",
                "days_remaining": 0,
                "expires_at": None,
                "modules": [],
                "subject": None,
                "is_cached": False,
            }

        status_val = str(raw_res.get("status") or "error")
        error_code = raw_res.get("error_code")
        message = str(raw_res.get("message") or "")
        result_raw = raw_res.get("result")
        result_data = result_raw if isinstance(result_raw, dict) else {}

        is_valid = status_val == "success" and result_data.get("license_status") in (
            "valid",
            "expiring_soon",
            "grace_period",
        ) and result_data.get("compatible", True) is not False

        effective_token = result_data.get("updated_token") or token
        jwt_claims = cls._extract_jwt_claims(effective_token) if effective_token else {}
        tier_info = (
            result_data.get("tier_info")
            if isinstance(result_data.get("tier_info"), dict)
            else (
                result_data.get("tier_metadata")
                if isinstance(result_data.get("tier_metadata"), dict)
                else (
                    cached_meta.get("tier_info")
                    if isinstance(cached_meta.get("tier_info"), dict)
                    else {}
                )
            )
        )

        resolved_tier = str(
            tier_info.get("id")
            or tier_info.get("slug")
            or result_data.get("tier")
            or jwt_claims.get("tier")
            or cached_meta.get("tier")
            or ("core" if not is_valid else "pro")
        ).strip().lower()

        default_display = (
            "Pluvira Pro" if resolved_tier == "pro"
            else ("Pluvira Ultra" if resolved_tier == "ultra"
            else ("14-Day Pro Trial" if resolved_tier == "trial"
            else ("Free Registered" if resolved_tier == "free"
            else (f"Pluvira {resolved_tier.title()}" if resolved_tier != "core" else "Pluvira Core"))))
        )

        resolved_display_name = (
            tier_info.get("display_name_full")
            or result_data.get("display_name_full")
            or jwt_claims.get("display_name_full")
            or cached_meta.get("display_name_full")
            or (default_display if is_valid or resolved_tier != "core" else None)
        )

        default_compact = (
            "PRO" if resolved_tier == "pro"
            else ("ULTRA" if resolved_tier == "ultra"
            else ("TRIAL" if resolved_tier == "trial"
            else ("FREE" if resolved_tier == "free"
            else (resolved_tier.upper() if resolved_tier != "core" else "CORE"))))
        )

        resolved_compact_name = (
            tier_info.get("name")
            or tier_info.get("compact_name")
            or result_data.get("compact_name")
            or jwt_claims.get("compact_name")
            or cached_meta.get("compact_name")
            or cached_meta.get("name")
            or (default_compact if is_valid or resolved_tier != "core" else None)
        )

        default_icon = (
            "building-2" if resolved_tier in ("enterprise", "fleet", "org", "business")
            else ("users" if resolved_tier in ("family", "team", "home")
            else ("user-check" if resolved_tier == "free"
            else "sparkles"))
        )

        resolved_badge_icon = (
            tier_info.get("badge_icon")
            or result_data.get("badge_icon")
            or jwt_claims.get("badge_icon")
            or cached_meta.get("badge_icon")
            or default_icon
        )

        resolved_badge_color = (
            tier_info.get("badge_color")
            or result_data.get("badge_color")
            or jwt_claims.get("badge_color")
            or cached_meta.get("badge_color")
            or ("#0ea5e9" if resolved_tier == "free" else None)
        )

        resolved_badge_text_color = (
            tier_info.get("badge_text_color")
            or result_data.get("badge_text_color")
            or jwt_claims.get("badge_text_color")
            or cached_meta.get("badge_text_color")
            or ("#ffffff" if resolved_tier == "free" else None)
        )

        resolved_max_ips = (
            tier_info.get("default_max_ips")
            or tier_info.get("max_ips")
            or result_data.get("max_ips")
            or result_data.get("ips")
            or jwt_claims.get("max_ips")
            or jwt_claims.get("ips")
            or cached_meta.get("max_ips")
            or (2 if not is_valid else 20)
        )

        resolved_max_slots = (
            tier_info.get("max_slots")
            or result_data.get("max_slots")
            or jwt_claims.get("max_slots")
            or cached_meta.get("max_slots")
            or (7 if is_valid else 2)
        )

        resolved_backup_max_slots = (
            tier_info.get("backup_max_slots")
            or result_data.get("backup_max_slots")
            or jwt_claims.get("backup_max_slots")
            or cached_meta.get("backup_max_slots")
            or (10 if resolved_tier == "ultra" else (5 if is_valid else 1))
        )

        if is_valid and effective_token and save_cache:
            try:
                root_cache = Path(".license_cache")
                if root_cache.exists() and root_cache.resolve() != (settings.data_dir / ".license_cache").resolve():
                    try:
                        root_cache.unlink()
                    except Exception:
                        pass
                settings.data_dir.mkdir(parents=True, exist_ok=True)
                cache_file = settings.data_dir / ".license_cache"
                
                import json
                from datetime import datetime, timezone
                from backend.core.identity import get_device_hash
                
                cache_payload = {
                    "version": 1,
                    "token": effective_token.strip(),
                    "device_hash": get_device_hash(),
                    "tier": resolved_tier,
                    "display_name_full": resolved_display_name,
                    "compact_name": resolved_compact_name,
                    "badge_icon": resolved_badge_icon,
                    "badge_color": resolved_badge_color,
                    "badge_text_color": resolved_badge_text_color,
                    "max_ips": resolved_max_ips,
                    "max_slots": resolved_max_slots,
                    "backup_max_slots": resolved_backup_max_slots,
                    "tier_info": tier_info,
                    "last_online_handshake_utc": int(datetime.now(timezone.utc).timestamp()),
                    "last_online_status": "ok"
                }
                
                from backend.core.file_manager import FileManager
                temp_file = cache_file.with_suffix(f".tmp.{os.getpid()}")
                temp_file.write_text(json.dumps(cache_payload), encoding="utf-8")
                FileManager.atomic_write(temp_file, cache_file)
                
                if result_data.get("updated_token"):
                    logging.info("Silent license auto-renewal: new Ed25519 token persisted to cache.")
                    from backend.core.db import DatabaseManager
                    cloud_id = DatabaseManager.get_cloud_identity()
                    if cloud_id and cloud_id.get("uid"):
                        DatabaseManager.save_cloud_identity(
                            uid=cloud_id["uid"],
                            formatted_id=cloud_id.get("formatted_id", ""),
                            access_token=cloud_id.get("access_token"),
                            license_token=effective_token.strip(),
                            device_hash=cloud_id.get("device_hash"),
                        )
            except Exception as e:
                logging.warning(f"Failed to persist license token to cache: {e}")

        if result_data.get("update_recommended"):
            logging.warning("⚠️ System Notice: A recommended update is available for the Pluvira Pro engine.")

        grace_hours_remaining = None
        if result_data.get("license_status") == "grace_period":
            try:
                cache_file = settings.data_dir / ".license_cache"
                if cache_file.exists():
                    import json
                    cached_data = cache_file.read_text(encoding="utf-8").strip()
                    if cached_data.startswith("{"):
                        parsed = json.loads(cached_data)
                        last_online = parsed.get("last_online_handshake_utc", 0)
                        import time
                        now = int(time.time())
                        elapsed = now - last_online
                        remaining_sec = (48 * 3600) - elapsed
                        grace_hours_remaining = max(0, remaining_sec // 3600)
            except Exception:
                pass

        return {
            "valid": is_valid,
            "status": status_val,
            "error_code": error_code,
            "message": message,
            "license_status": result_data.get("license_status", "unlicensed" if not is_valid else "valid"),
            "tier": resolved_tier,
            "display_name_full": resolved_display_name,
            "compact_name": resolved_compact_name,
            "badge_icon": resolved_badge_icon,
            "badge_color": resolved_badge_color,
            "badge_text_color": resolved_badge_text_color,
            "max_ips": resolved_max_ips,
            "max_slots": resolved_max_slots,
            "backup_max_slots": resolved_backup_max_slots,
            "days_remaining": result_data.get("days_remaining"),
            "expires_at": result_data.get("expires_at"),
            "modules": result_data.get("modules", []),
            "subject": result_data.get("subject"),
            "is_cached": result_data.get("is_cached", False),
            "trial": bool(result_data.get("trial", False)),
            "pro_version": result_data.get("pro_version") or result_data.get("version") or (os.getenv("PLUVIRA_PRO_VERSION") or os.getenv("PLUVIRA_VERSION") or "").lstrip("v") or None,
            "update_recommended": bool(result_data.get("update_recommended", False)),
            "compatible": result_data.get("compatible", True),
            "min_version": result_data.get("min_version"),
            "updated_token": result_data.get("updated_token"),
            "tier_info": tier_info or None,
            "grace_hours_remaining": grace_hours_remaining,
        }

    @classmethod
    def ping(cls, custom_path: Optional[Path] = None) -> bool:
        """Pings the Pro binary over IPC to verify responsiveness.

        Args:
            custom_path (Optional[Path]): Override binary path.

        Returns:
            bool: True if binary responds with ok/pong status.
        """
        res = cls.execute_sync("ping", payload={}, timeout=3.0, custom_path=custom_path)
        return bool(res and isinstance(res, dict) and res.get("status") in ("ok", "pong", "success"))

    @staticmethod
    def is_binary_installed(custom_path: Optional[Path] = None) -> bool:
        """Checks if the Pro Rust executable binary exists on disk and is executable.

        Args:
            custom_path (Optional[Path]): Override binary path.

        Returns:
            bool: True if Pro binary exists and is executable, False otherwise.
        """
        binary_path = custom_path or settings.pro_binary_path
        return binary_path.exists() and os.access(binary_path, os.X_OK)

    @classmethod
    def is_available(cls, custom_path: Optional[Path] = None) -> bool:
        """Checks if the Pro Rust binary is installed and has an active valid license.

        Args:
            custom_path (Optional[Path]): Override binary path.

        Returns:
            bool: True if Pro binary is installed and license is valid, False otherwise.
        """
        if not cls.is_binary_installed(custom_path):
            return False
        license_info = cls.verify_license(custom_path)
        return bool(license_info.get("valid", False))

    @classmethod
    async def execute(
        cls,
        command: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Executes Pro Rust binary via Subprocess IPC passing JSON on stdin.

        Args:
            command (str): Command flag to pass to binary (e.g., 'auto-merge').
            payload (Optional[Dict[str, Any]]): Input JSON payload.
            timeout (float): Max execution timeout in seconds.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON output if successful, None on failure or fallback.
        """
        import time
        start_time = time.perf_counter()
        is_bootstrap_cmd = command in ("verify-license", "validate-license", "ping")

        if is_bootstrap_cmd:
            if not cls.is_binary_installed(custom_path):
                return None
        else:
            if not cls.is_available(custom_path):
                logging.debug(
                    f"[PRO IPC] Binary unavailable or unlicensed for command='{command}'. Direct fallback to Python Core."
                )
                return None
            logging.info(f"[PRO IPC] Invoking command='{command}' (timeout={timeout}s)...")

        binary_path = custom_path or settings.pro_binary_path
        payload_dict = dict(payload) if payload is not None else {}
        if not is_bootstrap_cmd:
            cached_tok = cls._get_cached_token()
            if cached_tok:
                if "token" not in payload_dict:
                    payload_dict["token"] = cached_tok
                if "license_token" not in payload_dict:
                    payload_dict["license_token"] = cached_tok
        input_data = json.dumps(payload_dict).encode("utf-8")

        try:
            proc = await asyncio.create_subprocess_exec(
                str(binary_path),
                "--command",
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data), timeout=timeout
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if stdout:
                try:
                    res_data = json.loads(stdout.decode("utf-8", errors="replace"))
                    if isinstance(res_data, dict):
                        if proc.returncode == 0:
                            res_data["ipc_duration_ms"] = round(elapsed_ms, 2)
                            if isinstance(res_data.get("result"), dict):
                                res_data["result"]["ipc_duration_ms"] = round(elapsed_ms, 2)
                            if is_bootstrap_cmd:
                                return res_data
                            if res_data.get("status") != "error" and not res_data.get("error_code"):
                                logging.info(
                                    f"[PRO IPC] Command '{command}' executed successfully in {elapsed_ms:.2f}ms (exit=0)."
                                )
                                return res_data
                            err_code = res_data.get("error_code", "UNKNOWN_ERROR")
                            err_msg = res_data.get("message", "Subprocess returned error status")
                            logging.warning(
                                f"[PRO IPC] Command '{command}' failed after {elapsed_ms:.2f}ms (exit=0, error={err_code}): {err_msg}. Falling back to Python Core."
                            )
                            return None

                        if is_bootstrap_cmd:
                            return res_data

                        if proc.returncode == 42:
                            cls.invalidate_cache()
                            logging.warning(
                                f"[PRO IPC] Command '{command}' exited with code 42 after {elapsed_ms:.2f}ms (Unlicensed / Threshold Exceeded). Falling back to Python Core."
                            )
                            return None

                        err_code = res_data.get("error_code", "UNKNOWN_ERROR")
                        err_msg = res_data.get("message", "Subprocess returned non-zero code")
                        logging.warning(
                            f"[PRO IPC] Command '{command}' failed after {elapsed_ms:.2f}ms (exit={proc.returncode}, error={err_code}): {err_msg}. Falling back to Python Core."
                        )
                        return None
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            if proc.returncode == 42:
                cls.invalidate_cache()
                logging.warning(
                    f"[PRO IPC] Command '{command}' exited with code 42 after {elapsed_ms:.2f}ms (Unlicensed / Threshold Exceeded). Falling back to Python Core."
                )
                return None

            err_msg = stderr.decode("utf-8", errors="replace") if stderr else "Non-zero exit code"
            logging.warning(
                f"[PRO IPC] Command '{command}' failed after {elapsed_ms:.2f}ms (exit={proc.returncode}): {err_msg}. Falling back to Python Core."
            )
            return None

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logging.warning(
                f"[PRO IPC] Command '{command}' timed out after {elapsed_ms:.2f}ms (timeout limit {timeout}s). Falling back to Python Core."
            )
            return None
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logging.warning(
                f"[PRO IPC] Command '{command}' encountered exception after {elapsed_ms:.2f}ms: {e}. Falling back to Python Core."
            )
            return None

    @classmethod
    def execute_sync(
        cls,
        command: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for ProBridge.execute with event-loop detection.

        Args:
            command (str): Command flag to pass to binary.
            payload (Optional[Dict[str, Any]]): Input JSON payload.
            timeout (float): Max execution timeout in seconds.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON output if successful, None on failure or fallback.
        """
        is_bootstrap_cmd = command in ("verify-license", "validate-license", "ping")

        if is_bootstrap_cmd:
            if not cls.is_binary_installed(custom_path):
                return None
        else:
            if not cls.is_available(custom_path):
                return None

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        lambda: asyncio.run(
                            cls.execute(command, payload, timeout, custom_path)
                        )
                    ).result(timeout=timeout + 1.0)
            else:
                return loop.run_until_complete(
                    cls.execute(command, payload, timeout, custom_path)
                )
        except Exception:
            try:
                return asyncio.run(
                    cls.execute(command, payload, timeout, custom_path)
                )
            except Exception as e:
                logging.debug(f"ProBridge execute_sync error: {e}. Falling back.")
                return None

    @classmethod
    async def enrich_metadata(
        cls,
        programmes: List[Dict[str, Any]],
        tmdb_api_key: str = "",
        tvdb_api_key: str = "",
        trakt_client_id: str = "",
        enable_tvmaze: bool = True,
        enable_wikipedia: bool = True,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro native metadata enrichment engine via IPC command 'enrich-metadata'.

        Args:
            programmes (List[Dict[str, Any]]): List of programme dictionaries with raw_title.
            tmdb_api_key (str): Optional TMDb API key.
            tvdb_api_key (str): Optional TheTVDB API key.
            trakt_client_id (str): Optional Trakt.tv client ID.
            enable_tvmaze (bool): Enable TVMaze fallback.
            enable_wikipedia (bool): Enable Wikipedia REST fallback.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: IPC response with enriched programmes, or None on fallback.
        """
        payload = {
            "programmes": programmes,
            "tmdb_api_key": tmdb_api_key,
            "tvdb_api_key": tvdb_api_key,
            "trakt_client_id": trakt_client_id,
            "enable_tvmaze": enable_tvmaze,
            "enable_wikipedia": enable_wikipedia,
        }
        return await cls.execute("enrich-metadata", payload=payload, timeout=20.0, custom_path=custom_path)

    @classmethod
    async def search_epg(
        cls,
        query: str,
        db_path: Optional[str] = None,
        genre: Optional[str] = None,
        min_rating: Optional[float] = None,
        diacritics_normalize: bool = True,
        limit: int = 50,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro sub-5ms fuzzy EPG search engine via IPC command 'search-epg'.

        Args:
            query (str): Programme search query.
            db_path (Optional[str]): Database path for zero-copy WAL queries.
            genre (Optional[str]): Optional genre filter.
            min_rating (Optional[float]): Minimum community rating.
            diacritics_normalize (bool): Enable NFD diacritics stripping.
            limit (int): Max results limit.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Search results payload, or None on fallback.
        """
        target_db = db_path or str(settings.data_dir / "pluvira_epg.db")
        payload = {
            "db_path": target_db,
            "query": query,
            "genre": genre,
            "min_rating": min_rating,
            "diacritics_normalize": diacritics_normalize,
            "limit": limit,
        }
        return await cls.execute("search-epg", payload=payload, timeout=10.0, custom_path=custom_path)

    @classmethod
    async def probe_stream(
        cls,
        stream_url: str,
        timeout_ms: int = 3000,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro native byte-range stream probe via IPC command 'probe-stream'.

        Args:
            stream_url (str): Target stream endpoint URL.
            timeout_ms (int): Inspection timeout in milliseconds.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Stream probe metrics or None on fallback.
        """
        payload = {
            "stream_url": stream_url,
            "timeout_ms": timeout_ms,
        }
        return await cls.execute("probe-stream", payload=payload, timeout=(timeout_ms / 1000.0) + 2.0, custom_path=custom_path)

    @classmethod
    async def auto_map_epg(
        cls,
        channels: List[Dict[str, Any]],
        epg_channels: List[Dict[str, Any]],
        similarity_threshold: float = 0.85,
        only_unmapped: bool = True,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro native fuzzy EPG auto-mapping engine via IPC command 'auto-map-epg'.

        Args:
            channels (List[Dict[str, Any]]): List of channels to match.
            epg_channels (List[Dict[str, Any]]): List of available EPG channel items.
            similarity_threshold (float): Minimum similarity threshold (0.50 to 1.00).
            only_unmapped (bool): Only match channels without an existing EPG mapping.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Match results payload or None on fallback.
        """
        payload = {
            "channels": channels,
            "epg_channels": epg_channels,
            "similarity_threshold": similarity_threshold,
            "only_unmapped": only_unmapped,
        }
        return await cls.execute("auto-map-epg", payload=payload, timeout=20.0, custom_path=custom_path)

    @classmethod
    async def cascade_rewrite(
        cls,
        main_db_path: Optional[str] = None,
        epg_db_path: Optional[str] = None,
        batch_size: int = 10000,
        options: Optional[Dict[str, Any]] = None,
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro native Turbo Cascade Rewrite engine via IPC command 'cascade-rewrite'.

        Args:
            main_db_path (Optional[str]): Path to pluvira_main.db.
            epg_db_path (Optional[str]): Path to pluvira_epg.db.
            batch_size (int): Chunk batch processing size.
            options (Optional[Dict[str, Any]]): Additional execution flags.
            custom_path (Optional[Path]): Override binary path.

        Returns:
            Optional[Dict[str, Any]]: Execution metrics dictionary or None on fallback.
        """
        target_main = main_db_path or str(settings.data_dir / "pluvira_main.db")
        target_epg = epg_db_path or str(settings.data_dir / "pluvira_epg.db")
        payload = {
            "command": "cascade-rewrite",
            "main_db_path": target_main,
            "epg_db_path": target_epg,
            "batch_size": batch_size,
            "options": options or {"force_proxy_default": False, "normalize_names": True},
        }
        return await cls.execute("cascade-rewrite", payload=payload, timeout=60.0, custom_path=custom_path)

    @classmethod
    async def match_stream_candidates(
        cls,
        personal_channels: List[Dict[str, Any]],
        catalog_channels: List[Dict[str, Any]],
        custom_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Invokes Pro native batch stream candidate matcher via IPC command 'match-stream-candidates'."""
        payload = {
            "personal_channels": personal_channels,
            "catalog_channels": catalog_channels,
        }
        return await cls.execute("find-duplicate-clusters", payload=payload, timeout=20.0, custom_path=custom_path)
