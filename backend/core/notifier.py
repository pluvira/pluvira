"""Basic notification dispatcher service for Python Core."""

import logging
from datetime import datetime
from typing import List, Optional, Union, Dict, Any

from backend.config.models import NotificationSettings, GlobalConfig


class Notifier:
    """Basic notification dispatcher for Python Core."""

    @classmethod
    def from_config(cls, config: Optional[GlobalConfig] = None) -> "Notifier":
        """Factory method to instantiate Notifier directly from GlobalConfig or SQLite repository.

        Args:
            config (Optional[GlobalConfig]): GlobalConfig instance or None.

        Returns:
            Notifier: Configured Notifier instance.
        """
        try:
            from backend.core.notification_repository import NotificationRepository
            sqlite_notif = NotificationRepository().get_settings()
            return cls(config=sqlite_notif)
        except Exception:
            pass

        if config is not None and hasattr(config, "settings") and config.settings:
            notif = getattr(config.settings, "notifications", None)
            urls = getattr(config.settings, "notification_urls", None)
            if notif and (notif.enabled or notif.urls):
                return cls(config=notif, urls=urls)
            if urls:
                return cls(urls=urls)
            return cls(config=notif)

        return cls()

    def __init__(
        self,
        config: Optional[Union[NotificationSettings, List[str]]] = None,
        urls: Optional[List[str]] = None,
    ) -> None:
        """Initializes basic notification settings.

        Args:
            config (Optional[Union[NotificationSettings, List[str]]]): Settings or URL list.
            urls (Optional[List[str]]): Direct URL targets list.
        """
        if config is None and urls is None:
            try:
                from backend.core.notification_repository import NotificationRepository
                self.config = NotificationRepository().get_settings()
            except Exception:
                self.config = NotificationSettings()
        elif isinstance(config, NotificationSettings):
            self.config = config
        elif isinstance(config, list):
            self.config = NotificationSettings(urls=config)
        elif urls is not None:
            self.config = NotificationSettings(urls=urls)
        else:
            self.config = NotificationSettings()

        target_urls = list(self.config.urls) if self.config.urls else []
        if urls:
            for u in urls:
                if u and u not in target_urls:
                    target_urls.append(u)

        self.config.urls = target_urls
        self.urls = target_urls if self.config.enabled else []

    def is_event_enabled(self, event_name: str) -> bool:
        """Checks if global notifications are enabled and target event trigger is active.

        Args:
            event_name (str): Name of event trigger attribute.

        Returns:
            bool: True if event notification should be dispatched.
        """
        if not self.config.enabled or not self.urls:
            return False
        if self.config.events and hasattr(self.config.events, event_name):
            return bool(getattr(self.config.events, event_name))
        return True

    def dispatch_event(self, event_name: str, title: str, body: str, severity: str = "info") -> bool:
        """Dispatches basic notification event to console.

        Args:
            event_name (str): Event trigger name.
            title (str): Notification title string.
            body (str): Notification body string.
            severity (str): Severity level ('info', 'warning', 'critical', 'success').

        Returns:
            bool: True if dispatched, False if skipped.
        """
        if not self.is_event_enabled(event_name):
            return False

        self._send(title, body, notify_type=severity)
        return True

    def send_success(self, processed_channels: int, elapsed_time: float) -> None:
        """Sends acquisition run success summary notification.

        Args:
            processed_channels (int): Count of processed channels.
            elapsed_time (float): Execution duration in seconds.
        """
        if not self.is_event_enabled("update_success"):
            return

        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        title = "🟢 Pluvira: Update Successful"
        body = (
            f"The Pluvira update process completed successfully.\n\n"
            f"• Processed Channels: {processed_channels}\n"
            f"• Execution Time: {time_str}\n"
            f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._send(title, body, notify_type="info")

    def send_failure(self, error_message: str) -> None:
        """Sends acquisition run failure alert notification.

        Args:
            error_message (str): Failure error message.
        """
        if not self.is_event_enabled("update_failure"):
            return

        title = "🔴 Pluvira: Update Failed"
        body = (
            f"A critical error occurred during the Pluvira update process.\n\n"
            f"• Error Message: {error_message}\n"
            f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._send(title, body, notify_type="error")

    def send_link_test_report(
        self,
        total_tested: int,
        online_count: int,
        offline_count: int,
        new_ko_channels: List[str],
        recovered_count: int,
        elapsed_time: float,
    ) -> None:
        """Sends link test execution report notification.

        Args:
            total_tested (int): Total streams tested.
            online_count (int): Online count.
            offline_count (int): Offline count.
            new_ko_channels (List[str]): List of newly broken channel names.
            recovered_count (int): Recovered count.
            elapsed_time (float): Duration in seconds.
        """
        if not self.is_event_enabled("link_test_report"):
            return

        has_new_ko = len(new_ko_channels) > 0
        icon = "🔴" if has_new_ko else "🟢"
        title = f"{icon} Pluvira: Link Test Report"

        body = (
            f"Link test execution finished in {elapsed_time:.1f}s.\n\n"
            f"• Total Tested: {total_tested}\n"
            f"• Online (OK): {online_count}\n"
            f"• Offline (KO): {offline_count}\n"
            f"• Newly KO: {len(new_ko_channels)}\n"
            f"• Recovered: {recovered_count}\n\n"
            f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        notify_type = "warning" if has_new_ko else "info"
        self._send(title, body, notify_type=notify_type)

    @staticmethod
    def parse_target_url(url: str) -> Dict[str, Any]:
        """Parses notification webhook URL into provider DTO parameters.

        Args:
            url (str): Target webhook or Apprise-style URL.

        Returns:
            Dict[str, Any]: Dictionary with provider, target, and optional chat_id.
        """
        if not url:
            return {"provider": "generic", "target": ""}

        u_clean = url.strip()
        if u_clean.startswith(("tgram://", "tgrams://")):
            parts = u_clean.split("://", 1)[1].split("/", 1)
            token = parts[0]
            chat_id = parts[1] if len(parts) > 1 else ""
            return {
                "provider": "telegram",
                "target": f"bot{token}" if not token.startswith("bot") else token,
                "chat_id": chat_id,
            }
        elif u_clean.startswith(("discord://", "discords://")):
            parts = u_clean.split("://", 1)[1].rstrip("/")
            return {
                "provider": "discord",
                "target": f"https://discord.com/api/webhooks/{parts}",
            }
        elif u_clean.startswith(("slack://", "slacks://")):
            parts = u_clean.split("://", 1)[1].rstrip("/")
            return {
                "provider": "slack",
                "target": f"https://hooks.slack.com/services/{parts}",
            }
        return {
            "provider": "generic",
            "target": u_clean,
        }

    def _send(self, title: str, body: str, notify_type: str) -> None:
        """Internal helper to dispatch basic notification to console and delegate to Pro if active.

        Args:
            title (str): Title string.
            body (str): Body string.
            notify_type (str): Severity string.
        """
        msg = f"NOTIFICATION [{notify_type.upper()}]: {title} - {body}"
        lvl = notify_type.lower().strip()
        if lvl in ("critical", "error"):
            logging.error(msg)
        elif lvl in ("warning", "warn"):
            logging.warning(msg)
        else:
            logging.info(msg)

        from backend.core.pro_bridge import ProBridge
        if ProBridge.is_available() and self.urls:
            level = "warning" if notify_type == "warning" else ("error" if notify_type == "critical" else "info")
            for u in self.urls:
                target_info = self.parse_target_url(u)
                payload: Dict[str, Any] = {
                    "notification": {
                        "provider": target_info.get("provider", "generic"),
                        "target": target_info.get("target", u),
                        "title": title,
                        "body": body,
                        "level": level,
                    }
                }
                if target_info.get("chat_id"):
                    payload["notification"]["chat_id"] = target_info["chat_id"]
                try:
                    ProBridge.execute_sync("send-notification", payload=payload, timeout=5.0)
                except Exception as e:
                    logging.debug(f"Pro notification dispatch fallback: {e}")
