"""Configuration service layer encapsulating business logic for GlobalConfig management and presets."""

from typing import Dict, Any, Optional

from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import GlobalConfig
from backend.core.metadata_rule_repository import MetadataRuleRepository
from backend.core.notification_repository import NotificationRepository


class ConfigService:
    """Service handling global configuration retrieval, persistence, and preset profile application."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        metadata_rule_repo: Optional[MetadataRuleRepository] = None,
        notification_repo: Optional[NotificationRepository] = None,
    ) -> None:
        """Initializes configuration service with handler instance.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
            metadata_rule_repo (Optional[MetadataRuleRepository]): Override metadata rule repository instance.
            notification_repo (Optional[NotificationRepository]): Override notification repository instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.metadata_rule_repo = metadata_rule_repo or MetadataRuleRepository()
        self.notification_repo = notification_repo or NotificationRepository()

    def get_config(self) -> GlobalConfig:
        """Retrieves global application configuration with relational metadata rewrites and notification settings.

        Returns:
            GlobalConfig: Pydantic configuration model with populated global rewrites and notifications.
        """
        config = self.config_handler.load_config()
        self.metadata_rule_repo.seed_default_rules_if_empty()
        config.settings.rewrites = self.metadata_rule_repo.get_global_rules()
        config.settings.notifications = self.notification_repo.get_settings()
        config.settings.notification_urls = list(config.settings.notifications.urls)
        return config

    def update_config(self, config_payload: GlobalConfig) -> GlobalConfig:
        """Persists updated global application configuration.

        Args:
            config_payload (GlobalConfig): Validated configuration payload.

        Returns:
            GlobalConfig: Saved configuration model.
        """
        if config_payload.settings.rewrites is not None:
            self.metadata_rule_repo.set_global_rules(config_payload.settings.rewrites)
        if config_payload.settings.notifications is not None:
            self.notification_repo.save_settings(config_payload.settings.notifications)
        elif config_payload.settings.notification_urls is not None:
            self.notification_repo.set_urls(config_payload.settings.notification_urls)

        self.config_handler.save_config(config_payload)
        config_payload.settings.rewrites = self.metadata_rule_repo.get_global_rules()
        config_payload.settings.notifications = self.notification_repo.get_settings()
        config_payload.settings.notification_urls = list(config_payload.settings.notifications.urls)
        try:
            from backend.services.mdns_service import get_mdns_service
            device_name = config_payload.settings.device_name or "Pluvira"
            mdns_cfg = config_payload.settings.mdns
            if mdns_cfg is not None:
                get_mdns_service().reload(device_name=device_name, mdns_config=mdns_cfg)
        except Exception as e:
            import logging
            logging.warning(f"Failed to reload mDNS service on config update: {e}")
        return config_payload

    def apply_notification_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applies a preset notification event profile to configuration.

        Args:
            preset_name (str): Preset profile name.

        Returns:
            Dict[str, Any]: Updated notification settings object.

        Raises:
            HTTPException: 400 Bad Request if preset name is invalid.
        """
        from backend.services.notification_service import NotificationService
        notif_service = NotificationService(repository=self.notification_repo, config_handler=self.config_handler)
        return notif_service.apply_preset(preset_name)
