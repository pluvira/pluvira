"""Notification service layer encapsulating business logic for notification testing and preset management."""

import logging
from typing import Dict, Any, Optional

from backend.config.models import NotificationSettings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.exceptions import ValidationDomainError
from backend.core.notifier import Notifier
from backend.core.notification_repository import NotificationRepository


class NotificationService:
    """Service handling manual notification testing, event preset profile application, and SQLite persistence."""

    def __init__(
        self,
        repository: Optional[NotificationRepository] = None,
        config_handler: Optional[YAMLConfigHandler] = None,
    ) -> None:
        """Initializes notification service with notification repository.

        Args:
            repository (Optional[NotificationRepository]): Override notification repository instance.
            config_handler (Optional[YAMLConfigHandler]): Legacy configuration handler parameter.
        """
        self.repository = repository or NotificationRepository()
        self.config_handler = config_handler or YAMLConfigHandler()

    def get_settings(self) -> NotificationSettings:
        """Retrieves current notification settings and target webhook URLs.

        Returns:
            NotificationSettings: Populated notification settings model.
        """
        return self.repository.get_settings()

    def update_settings(self, settings: NotificationSettings) -> NotificationSettings:
        """Persists updated notification settings directly to SQLite.

        Args:
            settings (NotificationSettings): Updated notification settings.

        Returns:
            NotificationSettings: Saved notification settings.
        """
        self.repository.save_settings(settings)
        return settings

    def send_test_notification(
        self,
        title: Optional[str] = None,
        body: Optional[str] = None,
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches a test notification message to all configured target notification URLs.

        Args:
            title (Optional[str]): Custom notification title string.
            body (Optional[str]): Custom notification body string.
            target_url (Optional[str]): Optional specific target URL to test.

        Returns:
            Dict[str, Any]: Operation result status dictionary.

        Raises:
            HTTPException: 400 Bad Request if notifications are disabled or no target URLs configured.
        """
        notif_cfg = self.repository.get_settings()

        if not notif_cfg or not notif_cfg.enabled:
            raise ValidationDomainError("Notifications are globally disabled in settings.")

        urls = [target_url.strip()] if target_url and target_url.strip() else notif_cfg.urls
        if not urls or not any(bool(u and u.strip()) for u in urls):
            raise ValidationDomainError("No notification target URLs configured.")

        from backend.core.pro_bridge import ProBridge
        if ProBridge.is_available():
            dispatched = 0
            for u in urls:
                target_info = Notifier.parse_target_url(u)
                payload: Dict[str, Any] = {
                    "notification": {
                        "provider": target_info.get("provider", "generic"),
                        "target": target_info.get("target", u),
                        "title": title or "🔔 Pluvira: Test Notification",
                        "body": body or "This is a test notification dispatched from Pluvira settings.",
                        "level": "info",
                    }
                }
                if target_info.get("chat_id"):
                    payload["notification"]["chat_id"] = target_info["chat_id"]

                pro_res = ProBridge.execute_sync("send-notification", payload=payload)
                if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
                    dispatched += 1

            if dispatched > 0:
                return {
                    "success": True,
                    "message": f"Test notification dispatched via Pro engine to {dispatched} target URL(s).",
                    "targets_count": dispatched,
                }

        notifier = Notifier(config=notif_cfg, urls=urls)
        msg_title = title or "🔔 Pluvira: Test Notification"
        msg_body = body or "This is a test notification dispatched from Pluvira settings."

        notifier._send(msg_title, msg_body, notify_type="info")
        logging.info(f"Dispatched basic test notification to console.")

        return {
            "success": True,
            "message": f"Basic test notification dispatched to console.",
            "targets_count": len(urls),
        }

    @staticmethod
    def apply_preset_to_settings(settings: NotificationSettings, preset_name: str) -> bool:
        """Applies a preset configuration profile to event toggles.

        Args:
            settings (NotificationSettings): Target notification settings.
            preset_name (str): Preset profile name.

        Returns:
            bool: True if applied, False if invalid name.
        """
        p_name = preset_name.lower().strip()
        valid_presets = {"all", "none", "simple", "balanced", "advanced", "hardware", "content"}
        if p_name not in valid_presets:
            return False

        from backend.config.models import NotificationEventConfig

        if p_name == "none":
            for field in NotificationEventConfig.model_fields.keys():
                if isinstance(getattr(settings.events, field), bool):
                    setattr(settings.events, field, False)
        elif p_name == "all":
            for field in NotificationEventConfig.model_fields.keys():
                if isinstance(getattr(settings.events, field), bool):
                    setattr(settings.events, field, True)
        else:
            settings.events.update_success = True
            settings.events.update_failure = True

        return True

    def apply_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applies a preset notification event profile to configuration.

        Args:
            preset_name (str): Preset profile name.

        Returns:
            Dict[str, Any]: Updated notification settings object.

        Raises:
            HTTPException: 400 Bad Request if preset name is invalid.
        """
        applied = self.repository.apply_preset(preset_name)
        if not applied:
            raise ValidationDomainError(f"Invalid notification preset name '{preset_name}'.")

        updated_settings = self.repository.get_settings()
        return updated_settings.model_dump()
