"""Exporter service for generating M3U playlist and XMLTV guide strings."""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any


class Exporter:
    """Generates M3U playlist and XMLTV guide strings from processed data."""

    @staticmethod
    def generate_m3u(channels: List[Dict[str, Any]]) -> str:
        """Generates M3U playlist string from processed channels list.

        Args:
            channels (List[Dict[str, Any]]): Processed channel models list.

        Returns:
            str: Formatted M3U playlist content.
        """
        lines = ["#EXTM3U"]
        for ch in channels:
            if not ch.get("is_included", True):
                continue

            extinf_line = ch.get("extinf") or f"#EXTINF:-1,{ch.get('name', 'Unknown')}"
            lines.append(extinf_line)

            options = list(ch.get("options", []))
            ua = ch.get("user_agent")
            if ua:
                ua_opt = f"#EXTVLCOPT:http-user-agent={ua}"
                if ua_opt not in options:
                    options.append(ua_opt)

            if options:
                lines.extend(options)

            lines.append(ch.get("url", ""))

        return "\n".join(lines)

    @staticmethod
    def generate_xmltv(channels: List[Dict[str, Any]], epg_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generates XMLTV guide XML string from channels and EPG programme data.

        Args:
            channels (List[Dict[str, Any]]): Processed channels list.
            epg_data (Dict[str, List[Dict[str, Any]]]): Map of EPG ID to programme dicts list.

        Returns:
            str: Formatted XMLTV guide content.
        """
        root = ET.Element("tv")

        added_epg_ids = set()
        for ch in channels:
            if not ch.get("is_included", True) or not ch.get("is_mapped"):
                continue

            epg_id = ch.get("epg_id")
            if not epg_id or epg_id in added_epg_ids:
                continue

            c_elem = ET.SubElement(root, "channel", id=epg_id)
            dn = ET.SubElement(c_elem, "display-name")
            dn.text = ch.get("name", "Unknown")

            logo_url = ch.get("logo")
            if logo_url:
                ET.SubElement(c_elem, "icon", src=logo_url)

            added_epg_ids.add(epg_id)

        for epg_id, programmes in epg_data.items():
            if epg_id not in added_epg_ids:
                continue

            for prog in programmes:
                p_elem = ET.SubElement(
                    root,
                    "programme",
                    start=prog.get("s", ""),
                    stop=prog.get("e", ""),
                    channel=epg_id,
                )
                title = ET.SubElement(p_elem, "title")
                title.text = prog.get("t", "")

                desc_text = prog.get("d")
                if desc_text:
                    desc = ET.SubElement(p_elem, "desc")
                    desc.text = desc_text

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
