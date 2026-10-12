"""Channel filtering and EPG matching engine."""

import re
from typing import Dict, List, Optional, Set, Union, Tuple, Any
from difflib import SequenceMatcher
from backend.config.models import Filters


class ChannelMerger:
    """Handles channel allow/deny filter checks and EPG ID matching."""

    def __init__(self) -> None:
        """Initializes cleaning and slug normalization regex patterns."""
        self.re_clean_tags = re.compile(
            r"(?i)(?:\s+|[\(\[])(?:HD|SD|4K|8K|FHD|UHD|H\.265|HEVC|\d{3,4}p\w*)\b[\)\]]?"
        )
        self.re_slug = re.compile(r"[^a-z0-9]")

    def is_allowed(
        self,
        channel_name: str,
        channel_attrs: Dict[str, str],
        filters: Filters,
        allow_channels: Optional[List[str]] = None,
        deny_channels: Optional[List[str]] = None,
    ) -> bool:
        """Evaluates channel against allow/deny filters.

        Args:
            channel_name (str): Display name of channel.
            channel_attrs (Dict[str, str]): Channel EXTINF attributes dictionary.
            filters (Filters): Regex filter rules.
            allow_channels (Optional[List[str]]): Explicit allowed channel names.
            deny_channels (Optional[List[str]]): Explicit denied channel names.

        Returns:
            bool: True if allowed, False if denied.
        """
        allow_list = allow_channels or []
        deny_list = deny_channels or []
        attrs = channel_attrs or {}
        filter_obj = filters or Filters()

        if channel_name in deny_list:
            return False

        if channel_name in allow_list:
            return True

        for deny_rule in filter_obj.deny:
            val = channel_name if deny_rule.field == "name" else attrs.get(deny_rule.field, "")
            try:
                if re.search(deny_rule.regex, val):
                    return False
            except Exception:
                continue

        if not filter_obj.allow:
            return True

        for allow_rule in filter_obj.allow:
            val = channel_name if allow_rule.field == "name" else attrs.get(allow_rule.field, "")
            try:
                if re.search(allow_rule.regex, val):
                    return True
            except Exception:
                continue

        return False

    def normalize_name(self, name: Optional[str], level: int = 1) -> str:
        """Normalizes channel name by removing tags or slugifying.

        Args:
            name (Optional[str]): Original channel name.
            level (int): Normalization level (1 = clean tags, 2 = slugify).

        Returns:
            str: Normalized string.
        """
        if not name:
            return ""

        if level == 1:
            return self.re_clean_tags.sub("", name).strip()
        elif level == 2:
            clean = self.re_clean_tags.sub("", name)
            return self.re_slug.sub("", clean.lower())
        return name

    def match_stream_confidence(
        self,
        target_name: str,
        target_epg_id: str,
        candidate_name: str,
        candidate_tvg_id: str = "",
        candidate_epg_id: str = "",
    ) -> Tuple[float, str]:
        """Calculates match confidence score (0.0 to 100.0) between target channel and candidate stream.

        Hierarchy:
            1. EPG ID exact match -> 100.0
            2. Normalized Name exact match -> 100.0
            3. Normalized Fuzzy match >= 90.0% -> High confidence auto-attach
            4. Normalized Fuzzy match 70.0% - 89.9% -> Suggestion queue
            5. Below 70.0% -> None

        Args:
            target_name (str): Target personal channel name.
            target_epg_id (str): Target personal channel EPG ID.
            candidate_name (str): Candidate stream name.
            candidate_tvg_id (str): Candidate tvg-id attribute.
            candidate_epg_id (str): Candidate matched EPG ID.

        Returns:
            Tuple[float, str]: Confidence score (0-100) and confidence tier string ('epg_match', 'name_match', 'suggestion', 'none').
        """
        if target_epg_id:
            if candidate_epg_id and target_epg_id == candidate_epg_id:
                return 100.0, "epg_match"
            if candidate_tvg_id and target_epg_id.endswith(f"::{candidate_tvg_id}"):
                return 100.0, "epg_match"

        norm_target = self.normalize_name(target_name, level=1).lower().strip()
        norm_candidate = self.normalize_name(candidate_name, level=1).lower().strip()

        if not norm_target or not norm_candidate:
            return 0.0, "none"

        if norm_target == norm_candidate:
            return 100.0, "name_match"

        len_t = len(norm_target)
        len_c = len(norm_candidate)
        max_possible_ratio = (2.0 * min(len_t, len_c)) / (len_t + len_c)
        if max_possible_ratio < 0.70:
            return round(max_possible_ratio * 100.0, 1), "none"

        tokens_t = set(norm_target.split())
        tokens_c = set(norm_candidate.split())
        if not (tokens_t & tokens_c) and (norm_target not in norm_candidate) and (norm_candidate not in norm_target):
            common_prefix = False
            for tt in tokens_t:
                for tc in tokens_c:
                    if len(tt) >= 3 and len(tc) >= 3 and tt[:3] == tc[:3]:
                        common_prefix = True
                        break
                if common_prefix:
                    break
            if not common_prefix:
                return 0.0, "none"

        sim_ratio = SequenceMatcher(None, norm_target, norm_candidate).ratio() * 100.0
        score = round(sim_ratio, 1)

        if score >= 90.0:
            return score, "name_match"
        elif score >= 70.0:
            return score, "suggestion"

        return score, "none"

    def match_channel(
        self,
        channel_name: str,
        tvg_id: str,
        epg_lookup_id: Union[Set[str], List[str]],
        epg_lookup_slug: Dict[str, str],
        overrides: Dict[str, str],
        epg_sources_order: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Matches channel name or tvg-id to namespaced EPG IDs via exact matching for Python Core.

        Returns:
            Optional[str]: Matched namespaced EPG ID if found, else None.
        """
        override_map = overrides or {}
        lookup_ids = epg_lookup_id or []

        if channel_name in override_map:
            override_val = override_map[channel_name]
            if not override_val or "::" not in override_val or override_val in lookup_ids:
                return override_val

        if tvg_id:
            if tvg_id in lookup_ids:
                return tvg_id
            for namespaced_id in lookup_ids:
                if namespaced_id.endswith(f"::{tvg_id}"):
                    return namespaced_id

        return None

    def batch_match_epg(
        self,
        channels: List[Dict[str, Any]],
        epg_channels_index: Union[List[Dict[str, Any]], Dict[str, str]],
        similarity_threshold: float = 0.85,
        only_unmapped: bool = True,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Matches a batch of channels against indexed EPG channels using exact and fuzzy matching.

        Hierarchy:
            1. tvg-id exact match against EPG channel raw_id or id -> confidence 100.0
            2. Slug / normalized name exact match -> confidence 100.0
            3. Fuzzy name similarity >= similarity_threshold (default 0.85)

        Args:
            channels (List[Dict[str, Any]]): List of channel dictionaries.
            epg_channels_index (Union[List[Dict[str, Any]], Dict[str, str]]): List or dict of EPG channels.
            similarity_threshold (float): Minimum fuzzy match ratio (0.50 - 1.00).
            only_unmapped (bool): If True, skips channels that already have an epg_id.
            source_filter (Optional[str]): Optional source name filter.

        Returns:
            List[Dict[str, Any]]: List of match objects:
                [{"channel_name": str, "source_name": str, "epg_id": str, "confidence": float, "match_type": str}]
        """
        epg_items: List[Dict[str, str]] = []
        if isinstance(epg_channels_index, dict):
            for epg_id, epg_name in epg_channels_index.items():
                raw_id = epg_id.split("::", 1)[1] if "::" in epg_id else epg_id
                epg_items.append({
                    "id": epg_id,
                    "raw_id": raw_id,
                    "name": epg_name,
                    "norm": self.normalize_name(epg_name, level=1).lower().strip(),
                    "slug": self.normalize_name(epg_name, level=2),
                })
        elif isinstance(epg_channels_index, list):
            for item in epg_channels_index:
                epg_id = item.get("id") or ""
                raw_id = item.get("raw_id") or (epg_id.split("::", 1)[1] if "::" in epg_id else epg_id)
                epg_name = item.get("name") or ""
                epg_items.append({
                    "id": epg_id,
                    "raw_id": raw_id,
                    "name": epg_name,
                    "norm": self.normalize_name(epg_name, level=1).lower().strip(),
                    "slug": self.normalize_name(epg_name, level=2),
                })

        matches: List[Dict[str, Any]] = []

        for ch in channels:
            ch_source = ch.get("source") or ""
            if source_filter and ch_source != source_filter:
                continue

            existing_epg = ch.get("epg_id")
            if only_unmapped and existing_epg:
                continue

            ch_name = ch.get("name") or ""
            orig_data = ch.get("original_data") or {}
            tvg_id = (
                ch.get("tvg_id")
                or ch.get("tvg-id")
                or (orig_data.get("tvg-id") if isinstance(orig_data, dict) else "")
                or (orig_data.get("tvg_id") if isinstance(orig_data, dict) else "")
                or ""
            )

            matched_epg_id: Optional[str] = None
            confidence: float = 0.0
            match_type: str = "none"

            # 1. tvg-id exact match
            if tvg_id:
                tvg_lower = tvg_id.lower()
                for e_item in epg_items:
                    if (
                        e_item["raw_id"].lower() == tvg_lower
                        or e_item["id"].lower() == tvg_lower
                        or e_item["id"].lower().endswith(f"::{tvg_lower}")
                    ):
                        matched_epg_id = e_item["id"]
                        confidence = 100.0
                        match_type = "tvg_id_exact"
                        break

            # 2. Normalized name exact match
            norm_ch = self.normalize_name(ch_name, level=1).lower().strip()
            if not matched_epg_id and norm_ch:
                for e_item in epg_items:
                    if e_item["norm"] == norm_ch:
                        matched_epg_id = e_item["id"]
                        confidence = 100.0
                        match_type = "name_exact"
                        break

            # 3. Slug exact match
            slug_ch = self.normalize_name(ch_name, level=2)
            if not matched_epg_id and slug_ch:
                for e_item in epg_items:
                    if e_item["slug"] == slug_ch:
                        matched_epg_id = e_item["id"]
                        confidence = 100.0
                        match_type = "slug_exact"
                        break

            # 4. Fuzzy name match
            if not matched_epg_id and norm_ch:
                best_score = 0.0
                best_epg: Optional[str] = None
                len_ch = len(norm_ch)
                for e_item in epg_items:
                    if not e_item["norm"]:
                        continue
                    len_epg = len(e_item["norm"])
                    if (2.0 * min(len_ch, len_epg)) / (len_ch + len_epg) < similarity_threshold:
                        continue
                    ratio = SequenceMatcher(None, norm_ch, e_item["norm"]).ratio()
                    if ratio > best_score:
                        best_score = ratio
                        best_epg = e_item["id"]

                if best_epg and best_score >= similarity_threshold:
                    matched_epg_id = best_epg
                    confidence = round(best_score * 100.0, 1)
                    match_type = "fuzzy"

            if matched_epg_id:
                matches.append({
                    "channel_name": ch_name,
                    "source_name": ch_source,
                    "epg_id": matched_epg_id,
                    "confidence": confidence,
                    "match_type": match_type,
                })

        return matches
