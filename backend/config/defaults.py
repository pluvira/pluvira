"""Default rich YAML configuration generator."""

import secrets
from ruamel.yaml.comments import CommentedMap
from backend.config.settings import settings
from backend.config.models import RewriteRule


def get_default_global_rules() -> list[RewriteRule]:
    """Returns initial default global rewrite rules for new installations or factory reset."""
    return [
        RewriteRule(
            field="name",
            pattern=r"(?i)\s*[\(\[]?(?:1080p|720p|576p|480p|4K|UHD|FHD|Full\s*HD|FullHD|HD|SD|HEVC|Geo[- ]?locked|Geo[- ]?blocked)\b[\)\]]?",
            replacement="",
            mode="regex",
            enabled=True,
            description="Remove quality, resolution, and geo-restriction tags from channel names",
        ),
        RewriteRule(
            field="url",
            pattern="http:",
            replacement="https:",
            mode="text",
            enabled=True,
            description="Apply HTTPS",
        ),
    ]


def get_default_config_yaml() -> CommentedMap:
    """Generates default CommentedMap YAML structure with comments and example sources.

    Returns:
        CommentedMap: Default configuration YAML structure.
    """
    default_yaml = CommentedMap()
    default_yaml["version"] = 1

    s_map = CommentedMap()
    s_map["output_m3u"] = str(settings.data_dir / "pluvira.m3u")
    s_map["output_epg"] = str(settings.data_dir / "pluvira_epg.xml")
    s_map["temp_dir"] = str(settings.temp_dir)
    s_map["device_name"] = "Pluvira"
    s_map["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    s_map["epg_retention_days"] = 7
    s_map["search_debounce_ms"] = 300
    s_map["onboarding_completed"] = False


    s_map["file_permissions"] = CommentedMap({"mode": "0644", "owner": "", "group": ""})


    s_map["link_test_settings"] = CommentedMap({"min_delay": 1.5, "max_delay": 3.5})
    s_map["mdns"] = CommentedMap({"enabled": True, "service_type": "_pluvira._tcp.local."})

    default_yaml["settings"] = s_map

    auth_map = CommentedMap({
        "enabled": False,
        "secret_key": secrets.token_urlsafe(32),
        "algorithm": "HS256",
        "token_expire_minutes": 1440,
        "username": "admin",
        "password": "admin",
    })
    default_yaml["auth"] = auth_map


    default_yaml.yaml_set_start_comment(
        "==============================================================================\n"
        " Pluvira Configuration File\n"
        "==============================================================================\n"
    )

    return default_yaml
