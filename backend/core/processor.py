"""DataProcessor service for on-the-fly channel filtering, rewrites, and EPG mapping."""

import json
import time
import logging
import hashlib
from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from backend.config.models import ChannelSlot
from backend.core.license_thresholds import LicenseThresholdManager

from backend.config.settings import settings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import SourceSettings, Filters, GlobalConfig, RewriteRule
from backend.core.merger import ChannelMerger
from backend.core.rewrite import RewriteService
from backend.core.link_status import link_status_repo
from backend.core.lock_manager import LockManager
from backend.core.models.channel import Channel
from backend.core.utils import StreamUtils
from backend.core.channel_filters import filter_channels_for_link_test
from backend.core.quality_analyzer import QualityAnalyzer
from backend.core.raw_database import RawDatabaseService
from backend.core.individual_rewrite_repository import IndividualRewriteRepository
from backend.core.channel_merge_repository import ChannelMergeRepository
from backend.core.epg_override_repository import EpgOverrideRepository
from backend.core.source_filter_repository import SourceFilterRepository
from backend.core.source_repository import SourceRepository
from backend.core.metadata_rule_repository import MetadataRuleRepository


class DataProcessor:
    """Processes raw SQLite databases into filtered channel models and maps EPG guides."""

    def __init__(
        self,
        handler: Optional[YAMLConfigHandler] = None,
        merger: Optional[ChannelMerger] = None,
        rewrite_service: Optional[RewriteService] = None,
        lock_manager: Optional[LockManager] = None,
        rewrite_repo: Optional[IndividualRewriteRepository] = None,
        merge_repo: Optional[ChannelMergeRepository] = None,
        epg_override_repo: Optional[EpgOverrideRepository] = None,
        source_filter_repo: Optional[SourceFilterRepository] = None,
        source_repo: Optional[SourceRepository] = None,
        metadata_rule_repo: Optional[MetadataRuleRepository] = None,
    ) -> None:
        """Initializes handler, merger, and database paths with optional dependency injection."""
        self.handler = handler or YAMLConfigHandler()
        self.merger = merger or ChannelMerger()
        self.rewrite_service = rewrite_service or RewriteService()
        self.lock_manager = lock_manager or LockManager()
        self.rewrite_repo = rewrite_repo or IndividualRewriteRepository()
        self.merge_repo = merge_repo or ChannelMergeRepository()
        self.epg_override_repo = epg_override_repo or EpgOverrideRepository()
        self.source_filter_repo = source_filter_repo or SourceFilterRepository()
        self.source_repo = source_repo or SourceRepository()
        self.metadata_rule_repo = metadata_rule_repo or MetadataRuleRepository()

    def _analyze_and_notify(
        self, processed_list: List[Dict[str, Any]], config: GlobalConfig, epg_sources_order: List[str], duration: float
    ) -> None:
        """Analyzes processed data for issues and dispatches notifications delegating to QualityAnalyzer."""
        QualityAnalyzer.analyze_processed_channels(processed_list, config, epg_sources_order, duration)

    def check_epg_future_coverage(self, config: Optional[GlobalConfig] = None, all_epg: Optional[Dict[str, Any]] = None) -> float:
        """Inspects raw_epg for future programme coverage delegating to QualityAnalyzer."""
        if not config:
            config = self.handler.load_config()
        return QualityAnalyzer.check_epg_future_coverage(config, all_epg)

    def get_epg_data(
        self, epg_ids: Set[str], config: Optional[GlobalConfig] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieves raw EPG programme schedules for target channel IDs."""
        if not epg_ids:
            return {}
        if not config:
            config = self.handler.load_config()

        try:
            db_service = RawDatabaseService(data_dir=settings.data_dir, temp_dir=settings.temp_dir)
            all_epg = db_service.load_existing_raw_epg(channel_ids=epg_ids)
            self.check_epg_future_coverage(config=config, all_epg=all_epg)
            if not all_epg:
                return {}

            result: Dict[str, List[Dict[str, Any]]] = {}
            for eid in epg_ids:
                if eid in all_epg:
                    result[eid] = all_epg[eid]
                elif "::" in eid:
                    raw_id = eid.split("::", 1)[1]
                    if raw_id in all_epg:
                        result[eid] = all_epg[raw_id]
                else:
                    for k, progs in all_epg.items():
                        if "::" in k and k.split("::", 1)[1] == eid:
                            result[eid] = progs
                            break
            return result
        except Exception as e:
            logging.error(f"Failed to read EPG data: {e}")
            return {}

    def get_channels_for_link_test(
        self, filters: Dict[str, Any], config: Optional[GlobalConfig] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves processed channels filtered for link scanner task.

        Args:
            filters (Dict[str, Any]): Filter parameters dictionary.
            config (Optional[GlobalConfig]): Global configuration override.

        Returns:
            List[Dict[str, Any]]: Filtered channel models list.
        """
        channels = self.get_processed_channels(config=config)
        return filter_channels_for_link_test(channels, filters)

    def _resolve_force_proxy(
        self,
        original_url: str,
        source_name: str,
        config: Optional[GlobalConfig] = None,
        individual_rules: Optional[List[RewriteRule]] = None,
    ) -> bool:
        """Resolves whether a channel requires CORS proxying following global -> source -> individual hierarchy."""
        global_force_proxy = bool(getattr(config.settings, "force_proxy", False)) if config and config.settings else False
        db_sources = self.source_repo.get_all_sources()
        active_sources = db_sources if db_sources else (config.sources if config and config.sources else [])
        src_cfg = next((s for s in active_sources if s.name == source_name), None)
        source_force_proxy = bool(getattr(src_cfg.settings, "force_proxy", False)) if src_cfg and src_cfg.settings else False

        rules = individual_rules
        if rules is None and config and hasattr(config, "individual_rewrites") and config.individual_rewrites:
            rules = config.individual_rewrites.get(original_url, [])
        if rules is None:
            rules = self.rewrite_repo.get_by_url(original_url)

        individual_force_proxy = any(
            r.enabled and r.field == "force_proxy" and str(r.replacement).lower() in ("true", "1", "yes")
            for r in (rules or [])
        )
        return global_force_proxy or source_force_proxy or individual_force_proxy

    def _resolve_link_entry(self, original_url: str, url: str) -> Any:
        """Resolves link status entry checking original_url first with fallback to current url."""
        st_entry = link_status_repo.get_status(original_url)
        if st_entry.status == "unchecked" and url:
            alt_entry = link_status_repo.get_status(url)
            if alt_entry.status != "unchecked":
                st_entry = alt_entry
        return st_entry

    def _get_bookmarked_urls_map(self) -> Dict[str, Set[str]]:
        """Retrieves mapping of stream URLs to set of personal playlist IDs containing them."""
        bookmarked_map: Dict[str, Set[str]] = {}
        try:
            from backend.core.db import db_manager
            conn = db_manager.get_connection(db_manager.get_db_path())
            with conn:
                cursor = conn.execute(
                    """
                    SELECT pc.playlist_id, cs.url
                    FROM channel_slots cs
                    JOIN personal_channels pc ON cs.personal_channel_id = pc.id
                    """
                )
                for pl_id, s_url in cursor.fetchall():
                    if s_url not in bookmarked_map:
                        bookmarked_map[s_url] = set()
                    bookmarked_map[s_url].add(pl_id)
        except Exception:
            pass
        return bookmarked_map

    def get_processed_channels(
        self,
        config: Optional[GlobalConfig] = None,
        include_backups: bool = False,
        skip_rewrite: bool = False,
    ) -> List[Dict[str, Any]]:
        """Processes raw channels, applies rewrites, and maps EPG IDs using caching.

        Args:
            config (Optional[GlobalConfig]): Configuration override.
            include_backups (bool): Whether to include failover backup channels.

        Returns:
            List[Dict[str, Any]]: List of processed channel dictionaries.
        """
        start_proc = time.perf_counter()
        if not skip_rewrite and self.lock_manager.is_locked():
            logging.info("System is currently updating RAW data. Results might be inconsistent.")

        db_service = RawDatabaseService(data_dir=settings.data_dir, temp_dir=settings.temp_dir)
        raw_data = db_service.load_existing_channels()

        if not raw_data:
            return []
        if not config:
            config = self.handler.load_config()

        bookmarked_map = self._get_bookmarked_urls_map()

        db_sources = self.source_repo.get_all_sources()
        active_sources = db_sources if db_sources else (config.sources if config and config.sources else [])
        db_epg_sources = self.source_repo.get_all_epg_sources()
        active_epg_sources = db_epg_sources if db_epg_sources else (config.epg_sources if config and config.epg_sources else [])

        disabled_epg_sources = {
            s.name for s in active_epg_sources if not getattr(s, "enabled", True)
        }

        epg_index: Dict[str, str] = {}
        raw_epg_index = db_service.load_existing_epg_index()
        if raw_epg_index:
            for k, v in raw_epg_index.items():
                if "::" in k:
                    epg_source_name = k.split("::", 1)[0]
                    if epg_source_name in disabled_epg_sources:
                        continue
                epg_index[k] = v

        epg_sources_order = [
            s.name for s in active_epg_sources if getattr(s, "enabled", True)
        ]

        epg_lookup_ids: List[str] = []
        for epg_src_name in epg_sources_order:
            for k in epg_index.keys():
                if k.startswith(f"{epg_src_name}::") and k not in epg_lookup_ids:
                    epg_lookup_ids.append(k)
        for k in epg_index.keys():
            if k not in epg_lookup_ids:
                epg_lookup_ids.append(k)


        epg_lookup_slugs = {}
        for epg_src_name in epg_sources_order:
            for k, v in epg_index.items():
                if k.startswith(f"{epg_src_name}::"):
                    slug = self.merger.normalize_name(v, 2)
                    if slug and slug not in epg_lookup_slugs:
                        epg_lookup_slugs[slug] = k
        for k, v in epg_index.items():
            slug = self.merger.normalize_name(v, 2)
            if slug and slug not in epg_lookup_slugs:
                epg_lookup_slugs[slug] = k

        db_rewrites = self.rewrite_repo.get_all_grouped()
        all_individual_rewrites = db_rewrites if db_rewrites else (config.individual_rewrites if config and hasattr(config, "individual_rewrites") and config.individual_rewrites else {})

        all_source_filters = self.source_filter_repo.get_all_grouped()
        all_source_rules = self.metadata_rule_repo.get_all_source_rules_grouped()
        db_global_rules = self.metadata_rule_repo.get_global_rules()
        global_rules = (
            db_global_rules
            if db_global_rules
            else (config.settings.rewrites if config and config.settings and config.settings.rewrites else [])
        )
        global_overrides, source_overrides_map = self.epg_override_repo.get_all_grouped()

        from backend.core.pro_bridge import ProBridge

        used_pro_rewrite = False
        pro_processed_map: Dict[str, Dict[str, Any]] = {}
        if ProBridge.is_available():
            try:
                pro_res = None if skip_rewrite else ProBridge.execute_sync(
                    "cascade-rewrite",
                    payload={
                        "command": "cascade-rewrite",
                        "main_db_path": str(settings.data_dir / "pluvira_main.db"),
                        "epg_db_path": str(settings.data_dir / "pluvira_epg.db"),
                        "batch_size": 10000,
                        "options": {
                            "force_proxy_default": bool(getattr(config.settings, "force_proxy", False)),
                            "normalize_names": True,
                        },
                    },
                    timeout=30.0,
                )
                if skip_rewrite or (pro_res and pro_res.get("status") == "success"):
                    loaded_pro = db_service.load_existing_processed_channels()
                    if loaded_pro:
                        pro_processed_map = {p["id"]: p for p in loaded_pro}
                        used_pro_rewrite = True
            except Exception as pe:
                logging.warning(f"Turbo cascade rewrite fallback to Python Core: {pe}")

        processed_list: List[Dict[str, Any]] = []
        for raw in raw_data:
            source_name = raw.get("s", "")
            source_cfg = next((s for s in active_sources if s.name == source_name), None)

            if not source_cfg or not getattr(source_cfg, "enabled", True):
                continue

            raw_attrs = {}
            if raw.get("g"):
                raw_attrs["group-title"] = raw["g"]
            if raw.get("l"):
                raw_attrs["tvg-logo"] = raw["l"]
            if raw.get("i"):
                raw_attrs["tvg-id"] = raw["i"]

            ch = Channel(
                extinf_line=raw.get("x", ""),
                url_line=raw.get("u", ""),
                name=raw.get("n", ""),
                attributes=raw_attrs,
            )

            source_ua = source_cfg.settings.user_agent if source_cfg and source_cfg.settings else ""
            ch.user_agent = StreamUtils.resolve_user_agent("", source_ua, config.settings.user_agent or "")

            unique_id = hashlib.md5(f"{source_name}{ch.name}{ch.original_url}".encode()).hexdigest()
            pro_item = pro_processed_map.get(unique_id) if used_pro_rewrite else None

            if pro_item:
                ch.name = pro_item["name"]
                ch.url = pro_item["url"]
                if pro_item.get("group_name"):
                    ch.attributes["group-title"] = pro_item["group_name"]
                if pro_item.get("logo"):
                    ch.attributes["tvg-logo"] = pro_item["logo"]
                if pro_item.get("user_agent"):
                    ch.user_agent = pro_item["user_agent"]
                rewrite_details = {"turbo": ["ProNative"]} if pro_item.get("is_modified") else {}
                is_modified = pro_item.get("is_modified", False)
                individual_rules = []
            else:
                source_rules = (
                    source_cfg.settings.rewrites
                    if (source_cfg and source_cfg.settings and source_cfg.settings.rewrites)
                    else all_source_rules.get(source_name, [])
                )
                individual_rules = all_individual_rewrites.get(ch.original_url, [])

                rewrite_details = self.rewrite_service.process_cascading(
                    ch, global_rules, source_rules, individual_rules
                )
                is_modified = bool(rewrite_details)

            filters_obj = (
                source_cfg.settings.filters
                if source_cfg.settings and source_cfg.settings.filters
                else (config.settings.filters or Filters())
            )
            src_filters = all_source_filters.get(source_name, {"allow": set(), "deny": set()})
            allow_set = set(source_cfg.settings.allow_channels or []) if (source_cfg and source_cfg.settings and source_cfg.settings.allow_channels) else set()
            allow_ch = list(allow_set.union(src_filters["allow"]).union(config.settings.allow_channels or []))

            deny_set = set(source_cfg.settings.deny_channels or []) if (source_cfg and source_cfg.settings and source_cfg.settings.deny_channels) else set()
            deny_ch = list(deny_set.union(src_filters["deny"]).union(config.settings.deny_channels or []))

            is_included = self.merger.is_allowed(
                ch.name, ch.attributes, filters_obj, allow_ch, deny_ch
            )

            src_overrides = source_overrides_map.get(source_name, {})
            overrides = {**global_overrides, **src_overrides}
            mapped_id = self.merger.match_channel(
                ch.name,
                ch.attributes.get("tvg-id", ""),
                epg_lookup_ids,
                epg_lookup_slugs,
                overrides,
                epg_sources_order,
            )

            is_forced_proxy = (
                pro_item.get("force_proxy", False)
                if pro_item
                else self._resolve_force_proxy(ch.original_url, source_name, config, individual_rules)
            )
            link_entry = self._resolve_link_entry(ch.original_url, ch.url)

            rewrites_impact = sorted(list({s for scopes in rewrite_details.values() for s in scopes}))
            pl_ids = sorted(list(bookmarked_map.get(ch.original_url, set()).union(bookmarked_map.get(ch.url, set()))))

            processed_list.append({
                "id": unique_id,
                "name": ch.name,
                "url": ch.url,
                "original_url": ch.original_url,
                "group": ch.get_field("group-title"),
                "logo": ch.get_field("tvg-logo"),
                "user_agent": ch.user_agent,
                "source": source_name,
                "is_included": is_included,
                "is_bookmarked": len(pl_ids) > 0,
                "bookmarked_playlist_ids": pl_ids,
                "epg_id": mapped_id,
                "is_mapped": bool(mapped_id),
                "link_status": link_entry.status,
                "cors_supported": link_entry.cors_supported,
                "needs_proxy": is_forced_proxy or link_entry.needs_proxy,
                "rewrites": rewrites_impact,
                "rewrite_details": rewrite_details,
                "is_modified": is_modified,
                "extinf": ch.original_extinf,
                "original_data": {
                    "name": raw.get("n", ""),
                    "group": raw.get("g", ""),
                    "logo": raw.get("l", ""),
                    "url": raw.get("u", ""),
                },
            })

        db_merges = self.merge_repo.get_all()
        channel_merges_map = (
            db_merges
            if db_merges
            else (config.channel_merges if config and hasattr(config, "channel_merges") and config.channel_merges else {})
        )

        if channel_merges_map:
            url_source_map = {
                (ch["original_url"], ch.get("source", "")): ch for ch in processed_list
            }
            url_map = {ch["original_url"]: ch for ch in processed_list}

            primary_keys = {
                (
                    merge_cfg.primary_stream.url,
                    getattr(merge_cfg.primary_stream, "source", "") or "",
                )
                for merge_cfg in channel_merges_map.values()
                if merge_cfg.primary_stream
            }
            primary_urls = {
                merge_cfg.primary_stream.url
                for merge_cfg in channel_merges_map.values()
                if merge_cfg.primary_stream
            }

            backup_keys_to_remove: Set[tuple[str, str]] = set()
            backup_urls_fallback: Set[str] = set()

            for master_key, merge_cfg in channel_merges_map.items():
                p_url = merge_cfg.primary_stream.url
                p_source = getattr(merge_cfg.primary_stream, "source", "") or ""
                primary_ch = url_source_map.get((p_url, p_source)) or url_map.get(p_url)

                if primary_ch:
                    if merge_cfg.name:
                        primary_ch["name"] = merge_cfg.name
                    if merge_cfg.logo:
                        primary_ch["logo"] = merge_cfg.logo
                    if merge_cfg.group:
                        primary_ch["group"] = merge_cfg.group
                    if merge_cfg.epg_id:
                        primary_ch["epg_id"] = merge_cfg.epg_id
                        primary_ch["is_mapped"] = True

                    resolved_backups = []
                    for b_stream in merge_cfg.backup_streams:
                        b_url = b_stream.url
                        b_source = getattr(b_stream, "source", "") or ""
                        if b_source:
                            if (b_url, b_source) not in primary_keys:
                                backup_keys_to_remove.add((b_url, b_source))
                        else:
                            if b_url not in primary_urls:
                                backup_urls_fallback.add(b_url)

                        b_ch = url_source_map.get((b_url, b_source)) or url_map.get(b_url)
                        b_ua = (
                            b_stream.user_agent
                            or merge_cfg.user_agent
                            or (b_ch.get("user_agent") if b_ch else "")
                            or config.settings.user_agent
                            or "Mozilla/5.0"
                        )
                        resolved_backups.append({
                            "url": b_stream.url,
                            "source": b_stream.source,
                            "user_agent": b_ua,
                        })

                    primary_ch["backup_streams"] = resolved_backups

            if (backup_keys_to_remove or backup_urls_fallback) and not include_backups:
                processed_list = [
                    ch
                    for ch in processed_list
                    if (ch["original_url"], ch.get("source", "")) not in backup_keys_to_remove
                    and (not backup_urls_fallback or ch["original_url"] not in backup_urls_fallback)
                ]

        return processed_list

    def auto_attach_streams_to_personal_channels(
        self, config: Optional[GlobalConfig] = None
    ) -> Dict[str, int]:
        """Scans catalog channels and attaches qualified streams to personal channels and suggestions.

        Args:
            config (Optional[GlobalConfig]): Global configuration instance.

        Returns:
            Dict[str, int]: Attached and suggestions count summary.
        """
        from backend.core.personal_repository import PersonalPlaylistRepository

        repo = PersonalPlaylistRepository(settings.data_dir)
        catalog_channels = self.get_processed_channels(config=config, include_backups=True, skip_rewrite=True)

        attached_count = 0
        suggestions_count = 0

        conn = repo.get_conn()
        with conn:
            cursor = conn.execute(
                "SELECT id, playlist_id, name, epg_id FROM personal_channels"
            )
            personal_channels = cursor.fetchall()
            if not personal_channels:
                return {"attached_count": 0, "suggestions_count": 0}

            slots_cursor = conn.execute(
                "SELECT id, personal_channel_id, slot_index, url, source, user_agent, health_score, is_locked, consecutive_errors, quarantined_at FROM channel_slots ORDER BY slot_index ASC"
            )
            slots_by_channel: Dict[str, List[ChannelSlot]] = {}
            for row in slots_cursor.fetchall():
                s = ChannelSlot(
                    id=row[0],
                    personal_channel_id=row[1],
                    slot_index=row[2],
                    url=row[3],
                    source=row[4],
                    user_agent=row[5],
                    health_score=row[6],
                    is_locked=bool(row[7]),
                    consecutive_errors=row[8],
                    quarantined_at=row[9],
                )
                slots_by_channel.setdefault(row[1], []).append(s)

            sug_cursor = conn.execute(
                "SELECT personal_channel_id, url FROM channel_suggestions"
            )
            sug_urls_by_channel: Dict[str, Set[str]] = {}
            for ch_id, url in sug_cursor.fetchall():
                sug_urls_by_channel.setdefault(ch_id, set()).add(url)

            from backend.core.pro_bridge import ProBridge
            if ProBridge.is_available():
                pro_payload = {
                    "personal_channels": [
                        {"id": r[0], "playlist_id": r[1], "name": r[2], "epg_id": r[3] or ""}
                        for r in personal_channels
                    ],
                    "catalog_channels": [
                        {
                            "name": c.get("name", ""),
                            "url": c.get("url") or c.get("original_url", ""),
                            "source": c.get("source", "Unknown"),
                            "user_agent": c.get("user_agent"),
                            "extinf": c.get("extinf", ""),
                            "epg_id": c.get("epg_id", ""),
                            "link_status": c.get("link_status", "unchecked"),
                        }
                        for c in catalog_channels
                    ],
                }
                pro_res = ProBridge.execute_sync(
                    "find-duplicate-clusters",
                    payload={"channels": pro_payload["catalog_channels"], "similarity_threshold": 0.80},
                    timeout=20.0,
                )
                if pro_res and pro_res.get("status") == "success":
                    res_data = pro_res.get("result", {})
                    pro_matches = res_data.get("matches", []) if isinstance(res_data, dict) else []
                    max_slots = LicenseThresholdManager.get_max_slots()

                    for m in pro_matches:
                        pch_id = m.get("personal_channel_id")
                        c_url = m.get("url")
                        if not pch_id or not c_url:
                            continue
                        current_slots = slots_by_channel.get(pch_id, [])
                        existing_urls = {s.url for s in current_slots}
                        existing_sug_urls = sug_urls_by_channel.get(pch_id, set())
                        tier = m.get("tier", "none")
                        confidence = float(m.get("confidence", 0.0))

                        if tier in ("epg_match", "name_match") and len(existing_urls) < max_slots and c_url not in existing_urls:
                            slot = ChannelSlot(
                                id=f"slot_{uuid.uuid4().hex[:12]}",
                                personal_channel_id=pch_id,
                                slot_index=len(current_slots),
                                url=c_url,
                                source=m.get("source", "Unknown"),
                                user_agent=m.get("user_agent"),
                                health_score=100.0,
                            )
                            current_slots.append(slot)
                            slots_by_channel[pch_id] = current_slots
                            existing_urls.add(c_url)
                            attached_count += 1
                            repo.reorder_and_save_slots(conn, pch_id, current_slots)
                        elif tier == "suggestion" and c_url not in existing_urls and c_url not in existing_sug_urls:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO channel_suggestions (id, personal_channel_id, url, source, user_agent, confidence_score, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    f"sug_{uuid.uuid4().hex[:12]}",
                                    pch_id,
                                    c_url,
                                    m.get("source", "Unknown"),
                                    m.get("user_agent"),
                                    confidence,
                                    datetime.now(timezone.utc).isoformat(),
                                ),
                            )
                            suggestions_count += 1
                            existing_sug_urls.add(c_url)

                    return {"attached_count": attached_count, "suggestions_count": suggestions_count}

            for pch_id, pl_id, pch_name, pch_epg in personal_channels:
                current_slots = slots_by_channel.get(pch_id, [])
                existing_urls = {s.url for s in current_slots}
                existing_sug_urls = sug_urls_by_channel.get(pch_id, set())
                slots_modified = False

                for candidate in catalog_channels:
                    c_url = candidate.get("url") or candidate.get("original_url", "")
                    if not c_url or c_url in existing_urls:
                        continue

                    c_name = candidate.get("name", "")
                    c_source = candidate.get("source", "Unknown")
                    c_ua = candidate.get("user_agent")
                    c_tvg = candidate.get("extinf", "")
                    c_epg = candidate.get("epg_id", "")

                    if pch_epg and c_epg and pch_epg == c_epg:
                        confidence, tier = 100.0, "epg_match"
                    elif pch_name.lower().strip() == c_name.lower().strip():
                        confidence, tier = 100.0, "name_match"
                    else:
                        confidence, tier = self.merger.match_stream_confidence(
                            target_name=pch_name,
                            target_epg_id=pch_epg or "",
                            candidate_name=c_name,
                            candidate_tvg_id=c_tvg,
                            candidate_epg_id=c_epg,
                        )

                    max_slots = LicenseThresholdManager.get_max_slots()
                    if tier in ("epg_match", "name_match") and len(existing_urls) < max_slots and c_url not in existing_urls:
                        slot = ChannelSlot(
                            id=f"slot_{uuid.uuid4().hex[:12]}",
                            personal_channel_id=pch_id,
                            slot_index=len(current_slots),
                            url=c_url,
                            source=c_source,
                            user_agent=c_ua,
                            health_score=100.0 if candidate.get("link_status") != "offline" else 0.0,
                        )
                        current_slots.append(slot)
                        existing_urls.add(c_url)
                        attached_count += 1
                        slots_modified = True
                    elif tier == "suggestion" and c_url not in existing_urls and c_url not in existing_sug_urls:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO channel_suggestions (id, personal_channel_id, url, source, user_agent, confidence_score, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                f"sug_{uuid.uuid4().hex[:12]}",
                                pch_id,
                                c_url,
                                c_source,
                                c_ua,
                                confidence,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                        suggestions_count += 1
                        existing_sug_urls.add(c_url)

                if slots_modified:
                    repo.reorder_and_save_slots(conn, pch_id, current_slots)

        return {"attached_count": attached_count, "suggestions_count": suggestions_count}
