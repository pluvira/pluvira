"""Domain channel model representing an IPTV M3U stream entry."""

import re
from typing import Dict, List, Optional
from backend.core.parsers import M3UParser


class Channel:
    """Represents an IPTV channel stream with immutable original_url identity key."""

    def __init__(
        self,
        extinf_line: str,
        url_line: str,
        options: Optional[List[str]] = None,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initializes channel instance from raw M3U lines and fallback attributes.

        Args:
            extinf_line (str): Raw #EXTINF header line.
            url_line (str): Raw stream URL line.
            options (Optional[List[str]]): Multiline tag options list.
            name (Optional[str]): Fallback display name if extinf_line is empty.
            attributes (Optional[Dict[str, str]]): Fallback attributes map.
        """
        self.original_extinf: str = extinf_line.strip() if extinf_line else ""
        self.url: str = url_line.strip() if url_line else ""
        self.original_url: str = self.url  # Immutable identity key
        self.options: List[str] = options if options is not None else []
        self.attributes: Dict[str, str] = attributes.copy() if attributes else {}
        self.name: str = name or ""
        self.user_agent: Optional[str] = None

        if self.original_extinf:
            self._parse_extinf()

        if not self.original_extinf and self.name:
            self.update_extinf()

    def _parse_extinf(self) -> None:
        """Parses EXTINF header line extracting attributes and display name."""
        name, attributes = M3UParser.parse_extinf_metadata(self.original_extinf)
        self.name = name
        self.attributes.update(attributes)

    def get_field(self, field: str) -> str:
        """Retrieves field value by attribute key or property name.

        Args:
            field (str): Field attribute name.

        Returns:
            str: Value string or empty fallback.
        """
        if field == "name":
            return self.name
        if field == "url":
            return self.url
        if field == "user_agent":
            return self.user_agent or ""
        return self.attributes.get(field, "")

    def update_extinf(self) -> None:
        """Reconstructs EXTINF line reflecting modified metadata and attributes."""
        sanitized_attrs = {k: str(v).replace('"', "") for k, v in self.attributes.items()}
        attrs_str = " ".join([f'{k}="{v}"' for k, v in sanitized_attrs.items()])
        duration = "-1"
        if self.original_extinf.startswith("#EXTINF:"):
            duration_match = re.match(r"#EXTINF:(-?\d+)", self.original_extinf)
            if duration_match:
                duration = duration_match.group(1)
        attrs_part = f" {attrs_str}" if attrs_str else ""
        self.original_extinf = f"#EXTINF:{duration}{attrs_part},{self.name}"
