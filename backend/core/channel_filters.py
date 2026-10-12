"""Channel filtering utility module for polite link scanner tasks."""

import re
import logging
from typing import List, Dict, Any


def filter_channels_for_link_test(channels: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filters processed channels for link scanner based on inclusion, status, regex, and source criteria.

    Args:
        channels (List[Dict[str, Any]]): List of processed channel models.
        filters (Dict[str, Any]): Filter parameters dictionary.

    Returns:
        List[Dict[str, Any]]: Filtered list of channels.
    """
    if not filters:
        return [c for c in channels if c.get("is_included", True)]

    filtered = []
    inc = filters.get("inclusion", "included_only")
    status_filter = filters.get("status_filter", "all")
    sources = set(filters.get("sources") or [])
    groups = set(filters.get("groups") or [])
    ch_names = set(filters.get("channel_names") or [])

    name_regex_str = filters.get("name_regex")
    name_regex = None
    if name_regex_str:
        try:
            name_regex = re.compile(name_regex_str, re.IGNORECASE)
        except Exception as e:
            logging.error(f"Invalid name_regex for link test filter '{name_regex_str}': {e}")

    for c in channels:
        is_inc = c.get("is_included", True)
        if inc == "included_only" and not is_inc:
            continue
        elif inc == "excluded_only" and is_inc:
            continue

        st = (c.get("link_status") or "unchecked").lower()
        if status_filter == "ok_only" and st != "online":
            continue
        elif status_filter == "ko_only" and st != "offline":
            continue
        elif status_filter == "unchecked_only" and st not in ["unchecked", ""]:
            continue

        if sources and c.get("source") not in sources:
            continue

        if groups and c.get("group") not in groups:
            continue

        if ch_names:
            c_name = c.get("name", "")
            if c_name not in ch_names:
                continue

        if name_regex:
            c_name = c.get("name", "")
            if not name_regex.search(c_name):
                continue

        filtered.append(c)

    max_c = filters.get("max_channels")
    if max_c and isinstance(max_c, int) and max_c > 0:
        filtered = filtered[:max_c]

    return filtered
