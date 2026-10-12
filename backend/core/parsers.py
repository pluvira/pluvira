"""M3U playlist and XMLTV guide parsing module."""

import os
import re
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Generator, Optional, Any
from datetime import datetime, timezone, timedelta


class M3UParser:
    """Parser for M3U and M3U8 playlists supporting multiline tags and UTF-8-SIG encoding."""

    @staticmethod
    def parse_extinf_metadata(extinf_line: str) -> Tuple[str, Dict[str, str]]:
        """Parses EXTINF header line extracting display name and attributes dictionary.

        Args:
            extinf_line (str): Raw #EXTINF line.

        Returns:
            Tuple[str, Dict[str, str]]: Tuple of (display_name, attributes_dict).
        """
        if not extinf_line:
            return "", {}

        in_quotes = False
        comma_index = -1
        for idx, char in enumerate(extinf_line):
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                comma_index = idx
                break

        if comma_index != -1:
            attrs_part = extinf_line[:comma_index].strip()
            name = extinf_line[comma_index + 1 :].strip()
        else:
            attrs_part = extinf_line
            name = ""

        attributes: Dict[str, str] = {}
        attr_pattern = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')
        for match in attr_pattern.finditer(attrs_part):
            attributes[match.group(1)] = match.group(2)

        return name, attributes

    @staticmethod
    def parse(file_path: str, substitutions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parses M3U/M3U8 playlist file into channel dictionaries.

        Args:
            file_path (str): Path to M3U playlist file.
            substitutions (List[Dict[str, Any]]): Legacy regex substitutions list.

        Returns:
            Tuple[List[Dict[str, Any]], List[str]]: Tuple of parsed channel dicts and parsing error messages.
        """
        channels: List[Dict[str, Any]] = []
        errors: List[str] = []

        if not os.path.exists(file_path):
            return channels, errors

        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            errors.append(f"File reading error: {e}")
            return channels, errors

        i = 0
        total_lines = len(lines)
        while i < total_lines:
            line = lines[i].strip()
            if not line or line.startswith("#EXTM3U"):
                i += 1
                continue

            if line.startswith("#EXTINF:"):
                extinf = M3UParser._apply_substitutions(line, substitutions)
                options: List[str] = []
                url = ""

                j = i + 1
                found_url = False
                while j < total_lines:
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    if next_line.startswith("#EXTINF:"):
                        break
                    elif next_line.startswith("#"):
                        substituted_opt = M3UParser._apply_substitutions(next_line, substitutions)
                        options.append(substituted_opt)
                        j += 1
                    else:
                        url = M3UParser._apply_substitutions(next_line, substitutions)
                        found_url = True
                        j += 1
                        break

                if not found_url:
                    errors.append(f"Line {i+1}: #EXTINF found without a valid stream URL.")
                else:
                    parsed_ch = M3UParser._parse_extinf_line(extinf, url, options)
                    channels.append(parsed_ch)
                i = j
            else:
                if line.startswith("#"):
                    known_tags = ["#EXTVLCOPT:", "#EXTGRP:", "#EXT-X-"]
                    if not any(line.startswith(t) for t in known_tags):
                        errors.append(f"Line {i+1}: Ignored unknown or malformed tag: {line[:50]}...")
                elif not (line.startswith("http") or line.startswith("/") or line.startswith(".")):
                    errors.append(f"Line {i+1}: Unexpected line content: {line[:50]}...")
                i += 1

        return channels, errors

    @staticmethod
    def _parse_extinf_line(extinf_line: str, url: str, options: List[str]) -> Dict[str, Any]:
        """Parses a single EXTINF line into a channel dictionary.

        Args:
            extinf_line (str): Raw #EXTINF line.
            url (str): Stream URL.
            options (List[str]): Multiline option lines.

        Returns:
            Dict[str, Any]: Extracted channel dictionary.
        """
        name, attributes = M3UParser.parse_extinf_metadata(extinf_line)

        return {
            "n": name,
            "u": url,
            "g": attributes.get("group-title", ""),
            "l": attributes.get("tvg-logo", ""),
            "i": attributes.get("tvg-id", ""),
            "x": extinf_line,
            "options": options,
        }

    @staticmethod
    def _apply_substitutions(text: str, subs: List[Dict[str, Any]]) -> str:
        """Applies regex substitutions to text string.

        Args:
            text (str): Input text.
            subs (List[Dict[str, Any]]): Substitutions list.

        Returns:
            str: Modified text string.
        """
        for sub in subs:
            if "pattern" in sub and "replacement" in sub:
                text = re.sub(sub["pattern"], sub["replacement"], text)
        return text


class XMLTVParser:
    """Streaming XMLTV Parser designed to extract raw data with minimal memory footprint."""

    _date_regex = re.compile(r"^(\d{14})(?:\s*([+-])(\d{2}):?(\d{2}))?$")

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parses and normalizes XMLTV dates with optional timezone offset colons.

        Args:
            date_str (str): XMLTV date string (e.g. 20260728120000 +02:00).

        Returns:
            Optional[datetime]: Timezone-aware datetime or None if invalid.
        """
        if not date_str:
            return None
        match = XMLTVParser._date_regex.match(date_str.strip())
        if not match:
            return None
        dt_part, sign, hours, minutes = match.groups()
        try:
            dt = datetime.strptime(dt_part, "%Y%m%d%H%M%S")
            if sign:
                offset_sign = 1 if sign == "+" else -1
                offset_hours = int(hours)
                offset_minutes = int(minutes)
                tz = timezone(offset_sign * timedelta(hours=offset_hours, minutes=offset_minutes))
                return dt.replace(tzinfo=tz)
            return dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            logging.error(f"Failed to parse XMLTV date '{date_str}': {e}")
            return None

    @staticmethod
    def iter_elements(xml_path: str, tag_name: str) -> Generator[ET.Element, None, None]:
        """Memory-efficient streaming generator for XMLTV elements.

        Args:
            xml_path (str): Path to XMLTV file.
            tag_name (str): Tag name to yield (e.g. channel or programme).

        Yields:
            ET.Element: ElementTree XML element.
        """
        if not os.path.exists(xml_path):
            return

        try:
            context = ET.iterparse(xml_path, events=("end",))
            for _, elem in context:
                if elem.tag == tag_name or elem.tag.endswith("}" + tag_name):
                    yield elem
                    elem.clear()
        except Exception as e:
            logging.error(f"Critical error parsing XMLTV file '{xml_path}': {e}")
            raise ValueError(f"XMLTV Structural Error: {e}")

    @staticmethod
    def get_child_text(element: Optional[ET.Element], child_name: str) -> str:
        """Retrieves child text ignoring XML namespaces.

        Args:
            element (Optional[ET.Element]): Parent XML element.
            child_name (str): Target child tag name.

        Returns:
            str: Child element text or empty string.
        """
        if element is None:
            return ""

        for child in element:
            if child.tag == child_name or child.tag.endswith("}" + child_name):
                return child.text or ""
        return ""
