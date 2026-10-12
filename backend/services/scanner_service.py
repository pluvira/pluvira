"""Scanner service layer encapsulating business logic for link testing, batch scanner tasks, and status reset."""

from typing import Dict, Any, List, Optional
from fastapi import BackgroundTasks

from backend.core.exceptions import ProcessLockedError

from backend.core.link_tester import verify_link_detailed
from backend.config.settings import settings
from backend.core.link_status import link_status_repo, LinkStatusRepository
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.core.scanner import run_link_test_batch_task, scanner_state
from backend.core.pro_bridge import ProBridge
from backend.core.db import db_manager


class ScannerService:
    """Service handling stream link testing, batch scanner execution, stop signals, and repository reset."""

    def __init__(
        self,
        repository: Optional[LinkStatusRepository] = None,
        personal_repo: Optional[PersonalPlaylistRepository] = None,
    ) -> None:
        """Initializes scanner service with repository instances.

        Args:
            repository (Optional[LinkStatusRepository]): Override link status repository instance.
            personal_repo (Optional[PersonalPlaylistRepository]): Override personal repository instance.
        """
        self.repository = repository or link_status_repo
        self.personal_repo = personal_repo or PersonalPlaylistRepository(settings.data_dir)

    async def test_single_link(self, url: str, original_url: Optional[str] = None, user_agent: str = "Mozilla/5.0") -> Dict[str, Any]:
        """Performs real-time HTTP link verification and trace analysis, saving result to status repository.

        Args:
            url (str): Target stream endpoint URL.
            original_url (Optional[str]): Original URL identity key.
            user_agent (str): User-Agent header string.

        Returns:
            Dict[str, Any]: Detailed link inspection result.
        """
        save_url = original_url or url
        if ProBridge.is_available():
            link_db_path = str(db_manager.get_db_path(self.repository.db_path))
            main_db_path = str(db_manager.get_db_path())
            pro_res = await ProBridge.execute(
                "batch-link-test",
                payload={
                    "items": [{"url": url, "original_url": save_url, "user_agent": user_agent}],
                    "link_status_db_path": link_db_path,
                    "epg_db_path": link_db_path,
                    "main_db_path": main_db_path,
                },
            )
            if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
                res_obj = pro_res.get("result") if isinstance(pro_res.get("result"), dict) else pro_res
                results = res_obj.get("results") or res_obj.get("items") or []
                if results and isinstance(results[0], dict):
                    first_res = results[0]
                    res_status = first_res.get("status", "unchecked")
                    res_code = first_res.get("code", 0)
                    res_cors = first_res.get("cors_supported", False)
                    res_proxy = first_res.get("needs_proxy", False)
                    res_err = first_res.get("error_message")
                    self.repository.update_status(
                        save_url,
                        res_status,
                        res_code,
                        cors_supported=res_cors,
                        needs_proxy=res_proxy,
                        error_message=res_err,
                    )
                    if url and url != save_url:
                        self.repository.update_status(
                            url,
                            res_status,
                            res_code,
                            cors_supported=res_cors,
                            needs_proxy=res_proxy,
                            error_message=res_err,
                        )
                    self._sync_slot_health(url, save_url, res_status, res_err)
                    return {
                        "status": res_status,
                        "code": res_code,
                        "cors_supported": res_cors,
                        "needs_proxy": res_proxy,
                        "trace": [f"[0.001s] Pro link test {res_status.upper()} for {url}"],
                        "url": first_res.get("url") or url,
                        "has_redirects": first_res.get("has_redirects", False),
                        "redirect_count": first_res.get("redirect_count", 0),
                    }

        res = await verify_link_detailed(url, user_agent)
        err_msg = None
        if res["status"] == "offline":
            for line in res.get("trace", []):
                if "Error during request:" in line:
                    err_msg = line.split("Error during request:", 1)[1].strip()
                    break
        self.repository.update_status(
            save_url,
            res["status"],
            res["code"],
            cors_supported=res.get("cors_supported", False),
            needs_proxy=res.get("needs_proxy", False),
            error_message=err_msg,
        )
        if url and url != save_url:
            self.repository.update_status(
                url,
                res["status"],
                res["code"],
                cors_supported=res.get("cors_supported", False),
                needs_proxy=res.get("needs_proxy", False),
                error_message=err_msg,
            )
        self._sync_slot_health(url, save_url, res["status"], err_msg)
        return res

    def trigger_batch_link_test(self, items: List[Dict[str, Any]], background_tasks: BackgroundTasks) -> Dict[str, str]:
        """Triggers background batch stream link testing task.

        Args:
            items (List[Dict[str, Any]]): List of link test item dicts.
            background_tasks (BackgroundTasks): FastAPI background tasks dependency.

        Returns:
            Dict[str, str]: Status message.

        Raises:
            HTTPException: 423 Locked if batch link scanner is already running.
        """
        if scanner_state["is_testing"]:
            raise ProcessLockedError("Batch link scanner is already running.")

        background_tasks.add_task(run_link_test_batch_task, items)
        return {"message": f"Batch link scanner task started for {len(items)} items."}

    def stop_batch_link_test(self) -> Dict[str, str]:
        """Sends stop signal to abort running batch link test.

        Returns:
            Dict[str, str]: Status message.
        """
        scanner_state["abort_requested"] = True
        return {"message": "Stop signal sent to batch link scanner."}

    def _sync_slot_health(
        self,
        url: str,
        original_url: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Synchronizes stream health score, consecutive errors, and slot reordering across personal channels."""
        self.personal_repo.sync_slot_health(url, original_url, status, error_message)

    def reset_status_database(self) -> Dict[str, str]:
        """Resets link status database cache and persistent repository.

        Returns:
            Dict[str, str]: Status message.
        """
        self.repository.reset_all()
        return {"message": "Link status database reset completed successfully."}

    def report_link_status(
        self,
        original_url: str,
        link_status: str,
        code: int = 0,
        cors_supported: bool = False,
        needs_proxy: bool = False,
        error_message: Optional[str] = None,
        source: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persists link status reported directly by client video player.

        Args:
            original_url (str): Channel original URL identity key.
            link_status (str): Status string ('online', 'offline', 'unchecked', 'redirect').
            code (int): HTTP response code or client error code.
            cors_supported (bool): Whether stream supports direct browser playback.
            needs_proxy (bool): Whether stream requires CORS proxy.
            error_message (Optional[str]): Optional client playback error description.
            source (Optional[str]): Source provider name.
            url (Optional[str]): Stream URL tested.

        Returns:
            Dict[str, Any]: Operation result dictionary.
        """
        clean_status = link_status.lower().strip()
        prev_entry = self.repository.get_status(original_url)
        prev_status = (prev_entry.status or "unchecked").lower()

        self.repository.update_status(
            original_url,
            clean_status,
            code,
            cors_supported=cors_supported,
            needs_proxy=needs_proxy,
            error_message=error_message,
        )
        if url and url != original_url:
            self.repository.update_status(
                url,
                clean_status,
                code,
                cors_supported=cors_supported,
                needs_proxy=needs_proxy,
                error_message=error_message,
            )
        self._sync_slot_health(url or original_url, original_url, clean_status, error_message)

        if clean_status == "offline" and prev_status == "online":
            try:
                from backend.core.notifier import Notifier
                notifier = Notifier.from_config()
                notifier.dispatch_event(
                    event_name="link_ko_detected",
                    title="🔴 Pluvira: Link KO Detected (Player)",
                    body=f"Stream went OFFLINE during playback (Code {code}).\nSource: {source or 'Unknown'}\nURL: {url or original_url}\nError: {error_message or 'Playback Failure'}",
                    severity="warning",
                )
            except Exception:
                pass
        elif clean_status == "online" and prev_status == "offline":
            try:
                from backend.core.notifier import Notifier
                notifier = Notifier.from_config()
                notifier.dispatch_event(
                    event_name="link_recovered",
                    title="🟢 Pluvira: Link Recovered (Player)",
                    body=f"Stream is back ONLINE (Code {code}).\nSource: {source or 'Unknown'}\nURL: {url or original_url}",
                    severity="info",
                )
            except Exception:
                pass

        return {
            "success": True,
            "original_url": original_url,
            "status": clean_status,
            "code": code,
            "cors_supported": cors_supported,
            "needs_proxy": needs_proxy,
        }
