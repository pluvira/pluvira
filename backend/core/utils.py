"""Utility functions for array manipulation and User-Agent resolution."""

import re
from typing import Any
from urllib.parse import urljoin, quote


class ParamUtils:
    """Utility class for API request parameter resolution."""

    @staticmethod
    def resolve_param(payload_val: Any, query_val: Any, default: Any) -> Any:
        """Resolves endpoint parameter prioritizing JSON payload over query param.

        Args:
            payload_val (Any): Value from payload object.
            query_val (Any): Value from query parameter.
            default (Any): Fallback default value.

        Returns:
            Any: Resolved parameter value.
        """
        if payload_val is not None:
            return payload_val
        if query_val is not None:
            return query_val
        return default


class StreamUtils:
    """Utility class for stream header resolution."""

    @staticmethod
    def resolve_user_agent(explicit_ua: str, source_ua: str, global_ua: str) -> str:
        """Resolves effective User-Agent following fallback hierarchy.

        Args:
            explicit_ua (str): Explicit channel/stream User-Agent.
            source_ua (str): Source-level User-Agent.
            global_ua (str): Global setting User-Agent.

        Returns:
            str: Resolved effective User-Agent string.
        """
        return explicit_ua or source_ua or global_ua or "Mozilla/5.0"

    @staticmethod
    def rewrite_m3u8_manifest(manifest_text: str, base_url: str, custom_user_agent: str = "") -> str:
        """Rewrites embedded URLs in M3U8 manifest to route through backend CORS proxy.

        Args:
            manifest_text (str): Raw M3U8 playlist content.
            base_url (str): Base URL of manifest for relative URL resolution.
            custom_user_agent (str): User-Agent header string to preserve in proxy query params.

        Returns:
            str: Rewritten M3U8 manifest content.
        """
        if not manifest_text:
            return ""

        def build_proxy_url(raw_url: str) -> str:
            resolved = urljoin(base_url, raw_url.strip())
            encoded_url = quote(resolved, safe="")
            proxy_path = f"/api/v1/stream/proxy?url={encoded_url}"
            if custom_user_agent:
                encoded_ua = quote(custom_user_agent, safe="")
                proxy_path += f"&user_agent={encoded_ua}"
            return proxy_path

        uri_pattern = re.compile(r'URI="([^"]+)"', re.IGNORECASE)
        rewritten_lines = []

        for line in manifest_text.splitlines():
            stripped = line.strip()
            if not stripped:
                rewritten_lines.append(line)
                continue

            if stripped.startswith("#"):
                if 'URI="' in line or 'uri="' in line:
                    def replace_uri(match: re.Match) -> str:
                        return f'URI="{build_proxy_url(match.group(1))}"'
                    line = uri_pattern.sub(replace_uri, line)
                rewritten_lines.append(line)
            else:
                rewritten_lines.append(build_proxy_url(stripped))

        return "\n".join(rewritten_lines)
