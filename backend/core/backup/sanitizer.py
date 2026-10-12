"""Sanitization and credential protection engine for backup exports and imports."""

import re
from typing import List, Optional
from copy import deepcopy

from backend.config.models import GlobalConfig
from backend.core.backup.bundle import BackupBundle

SANITIZED_PLACEHOLDER = "***SANITIZED***"


class BackupSanitizer:
    """Handles masking and restoring sensitive credentials in backup bundles."""

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitizes sensitive tokens or credentials from notification webhook URLs.

        Args:
            url (str): Target webhook or notification URL.

        Returns:
            str: Masked URL string.
        """
        if not url:
            return ""

        tgram_match = re.match(r"^(tgram(?:s)?://)([^/]+)(/.*)?$", url, re.IGNORECASE)
        if tgram_match:
            scheme, _, rest = tgram_match.groups()
            return f"{scheme}{SANITIZED_PLACEHOLDER}{rest or ''}"

        discord_match = re.match(r"^(discord(?:s)?://)([^/]+)/([^/]+)(/.*)?$", url, re.IGNORECASE)
        if discord_match:
            scheme, _, _, rest = discord_match.groups()
            return f"{scheme}{SANITIZED_PLACEHOLDER}/{SANITIZED_PLACEHOLDER}{rest or ''}"

        slack_match = re.match(r"^(slack(?:s)?://)([^/]+)/([^/]+)/([^/]+)(/.*)?$", url, re.IGNORECASE)
        if slack_match:
            scheme, _, _, _, rest = slack_match.groups()
            return f"{scheme}{SANITIZED_PLACEHOLDER}/{SANITIZED_PLACEHOLDER}/{SANITIZED_PLACEHOLDER}{rest or ''}"

        sanitized = url
        user_pass_match = re.match(r"^([a-zA-Z0-9+.-]+://)([^@:]+):([^@]+)@(.*)$", sanitized)
        if user_pass_match:
            scheme, _, _, rest = user_pass_match.groups()
            sanitized = f"{scheme}{SANITIZED_PLACEHOLDER}:{SANITIZED_PLACEHOLDER}@{rest}"

        sanitized = re.sub(
            r"([?&](?:token|auth|auth_token|key|password|pass|user|username|secret|api_key|apikey)=)[^&#\s]*",
            rf"\g<1>{SANITIZED_PLACEHOLDER}",
            sanitized,
            flags=re.IGNORECASE,
        )

        return sanitized

    @staticmethod
    def is_sanitized_value(val: Optional[str]) -> bool:
        """Checks whether a string value is empty or represents a sanitized placeholder.

        Args:
            val (Optional[str]): Target string to inspect.

        Returns:
            bool: True if sanitized or empty, False otherwise.
        """
        if val is None:
            return True
        v = val.strip()
        return v == "" or v == SANITIZED_PLACEHOLDER or v == "SANITIZED"

    @staticmethod
    def sanitize_bundle(bundle: BackupBundle) -> BackupBundle:
        """Creates a deep-copied BackupBundle with sensitive fields sanitized.

        Args:
            bundle (BackupBundle): Source backup bundle.

        Returns:
            BackupBundle: Sanitized backup bundle with sanitized flag set to True.
        """
        sanitized_bundle = deepcopy(bundle)
        sanitized_bundle.sanitized = True

        cfg = sanitized_bundle.config
        if cfg.auth:
            cfg.auth.password = SANITIZED_PLACEHOLDER
            cfg.auth.secret_key = SANITIZED_PLACEHOLDER

        if cfg.settings:
            if cfg.settings.notification_urls:
                cfg.settings.notification_urls = [
                    BackupSanitizer.sanitize_url(u) for u in cfg.settings.notification_urls
                ]
            if cfg.settings.notifications and cfg.settings.notifications.urls:
                cfg.settings.notifications.urls = [
                    BackupSanitizer.sanitize_url(u) for u in cfg.settings.notifications.urls
                ]

        if getattr(sanitized_bundle, "notification_targets", None):
            sanitized_bundle.notification_targets = [
                BackupSanitizer.sanitize_url(u) for u in sanitized_bundle.notification_targets
            ]

        if getattr(sanitized_bundle, "sources", None):
            for s in sanitized_bundle.sources:
                if isinstance(s, dict) and s.get("m3u_url"):
                    s["m3u_url"] = BackupSanitizer.sanitize_url(s["m3u_url"])

        if getattr(sanitized_bundle, "epg_sources", None):
            for s in sanitized_bundle.epg_sources:
                if isinstance(s, dict) and s.get("url"):
                    s["url"] = BackupSanitizer.sanitize_url(s["url"])

        if getattr(sanitized_bundle, "channel_merges", None):
            for m in sanitized_bundle.channel_merges.values():
                if isinstance(m, dict):
                    if isinstance(m.get("primary_stream"), dict) and m["primary_stream"].get("url"):
                        m["primary_stream"]["url"] = BackupSanitizer.sanitize_url(m["primary_stream"]["url"])
                    for b in m.get("backup_streams", []):
                        if isinstance(b, dict) and b.get("url"):
                            b["url"] = BackupSanitizer.sanitize_url(b["url"])

        if getattr(sanitized_bundle, "personal_channels", None):
            for pch in sanitized_bundle.personal_channels:
                if isinstance(pch, dict):
                    for slot in pch.get("slots", []):
                        if isinstance(slot, dict) and slot.get("url"):
                            slot["url"] = BackupSanitizer.sanitize_url(slot["url"])

        return sanitized_bundle

    @staticmethod
    def restore_url(sanitized_url: str, existing_urls: List[str]) -> str:
        """Restores original URL from existing URLs if sanitized placeholder matches.

        Args:
            sanitized_url (str): Potentially sanitized URL.
            existing_urls (List[str]): List of current active URLs on disk.

        Returns:
            str: Restored original URL or incoming URL.
        """
        if SANITIZED_PLACEHOLDER not in sanitized_url:
            return sanitized_url

        for orig in existing_urls:
            if BackupSanitizer.sanitize_url(orig) == sanitized_url:
                return orig

        return sanitized_url

    @staticmethod
    def restore_sanitized_fields(
        incoming_config: GlobalConfig, existing_config: GlobalConfig
    ) -> GlobalConfig:
        """Preserves existing credentials when incoming configuration contains sanitized values.

        Args:
            incoming_config (GlobalConfig): Configuration being imported.
            existing_config (GlobalConfig): Active configuration currently on disk.

        Returns:
            GlobalConfig: Mutated incoming configuration with restored credentials.
        """
        if incoming_config.auth and existing_config.auth:
            if BackupSanitizer.is_sanitized_value(incoming_config.auth.password):
                incoming_config.auth.password = existing_config.auth.password
            if BackupSanitizer.is_sanitized_value(incoming_config.auth.secret_key):
                incoming_config.auth.secret_key = existing_config.auth.secret_key

        existing_urls: List[str] = []
        if existing_config.settings:
            if existing_config.settings.notifications and existing_config.settings.notifications.urls:
                existing_urls = list(existing_config.settings.notifications.urls)
            elif existing_config.settings.notification_urls:
                existing_urls = list(existing_config.settings.notification_urls)

        if incoming_config.settings:
            if incoming_config.settings.notification_urls:
                incoming_config.settings.notification_urls = [
                    BackupSanitizer.restore_url(u, existing_urls)
                    for u in incoming_config.settings.notification_urls
                ]
            if incoming_config.settings.notifications and incoming_config.settings.notifications.urls:
                incoming_config.settings.notifications.urls = [
                    BackupSanitizer.restore_url(u, existing_urls)
                    for u in incoming_config.settings.notifications.urls
                ]

        if incoming_config.sources and existing_config.sources:
            existing_source_urls = [s.m3u_url for s in existing_config.sources if getattr(s, "m3u_url", None)]
            for s in incoming_config.sources:
                if getattr(s, "m3u_url", None):
                    s.m3u_url = BackupSanitizer.restore_url(s.m3u_url, existing_source_urls)

        if incoming_config.epg_sources and existing_config.epg_sources:
            existing_epg_urls = [s.url for s in existing_config.epg_sources if getattr(s, "url", None)]
            for s in incoming_config.epg_sources:
                if getattr(s, "url", None):
                    s.url = BackupSanitizer.restore_url(s.url, existing_epg_urls)

        return incoming_config
