"""Analytics calculator engine for global, per-source, and EPG metrics calculation."""

from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

from backend.config.settings import settings
from backend.config.models import GlobalConfig
from backend.core.parsers import XMLTVParser
from backend.core.raw_database import RawDatabaseService


class AnalyticsCalculator:
    """Calculates dashboard metrics for IPTV sources, EPG guides, and global health."""

    @staticmethod
    def calculate_dashboard_analytics(
        processed: List[Dict[str, Any]],
        config: Optional[GlobalConfig] = None,
        sources: Optional[List[Any]] = None,
        epg_sources: Optional[List[Any]] = None,
        epg_index: Optional[Dict[str, Any]] = None,
        raw_epg: Optional[Dict[str, Any]] = None,
        latest_history: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
        """Calculates per-source, global, and EPG metrics for dashboard.

        Args:
            processed (List[Dict[str, Any]]): Processed channel models list.
            config (Optional[GlobalConfig]): Global configuration instance.
            sources (Optional[List[Any]]): Pre-loaded IPTV sources list.
            epg_sources (Optional[List[Any]]): Pre-loaded EPG sources list.
            epg_index (Optional[Dict[str, Any]]): Pre-loaded EPG channels index.
            raw_epg (Optional[Dict[str, Any]]): Pre-loaded raw programmes map.
            latest_history (Optional[Any]): Pre-loaded latest history record.

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
            Tuple of (sources_stats, global_stats, epg_sources_stats).
        """
        if sources is None:
            from backend.core.source_repository import SourceRepository
            source_repo = SourceRepository()
            db_sources = source_repo.get_all_sources()
            configured_sources = db_sources if db_sources else (config.sources if config and hasattr(config, "sources") else [])
        else:
            configured_sources = sources

        sources_map: Dict[str, List[Dict[str, Any]]] = {}
        for ch in processed:
            src = ch.get("source", "Unknown")
            if src not in sources_map:
                sources_map[src] = []
            sources_map[src].append(ch)

        cfg_source_names = {s.name for s in configured_sources}
        all_source_names = sorted(list(cfg_source_names.union(sources_map.keys())))

        sources_stats: List[Dict[str, Any]] = []
        for src_name in all_source_names:
            src_cfg = next((s for s in configured_sources if s.name == src_name), None)
            is_enabled = getattr(src_cfg, "enabled", True) if src_cfg else True

            channels = sources_map.get(src_name, [])
            tot = len(channels)
            inc = [c for c in channels if c.get("is_included", True)]
            exc = [c for c in channels if not c.get("is_included", True)]

            inc_tot = len(inc)
            exc_tot = len(exc)

            inc_mapped = sum(1 for c in inc if c.get("is_mapped"))
            exc_mapped = sum(1 for c in exc if c.get("is_mapped"))

            epg_inc_pct = round((inc_mapped / inc_tot * 100.0), 1) if inc_tot > 0 else 0.0
            epg_exc_pct = round((exc_mapped / exc_tot * 100.0), 1) if exc_tot > 0 else 0.0

            online = sum(1 for c in inc if c.get("link_status") == "online")
            offline = sum(1 for c in inc if c.get("link_status") == "offline")
            unchecked = inc_tot - online - offline
            tested = online + offline
            link_health = round((online / tested * 100.0), 1) if tested > 0 else 0.0

            sources_stats.append({
                "name": src_name,
                "enabled": is_enabled,
                "status": "ACTIVE" if is_enabled else "DISABLED",
                "total_channels": tot,
                "included_channels": inc_tot,
                "excluded_channels": exc_tot,
                "epg_match_included_pct": epg_inc_pct,
                "epg_match_excluded_pct": epg_exc_pct,
                "online_links": online,
                "offline_links": offline,
                "unchecked_links": unchecked,
                "link_health_pct": link_health,
            })

        tot_all = len(processed)
        all_inc = [c for c in processed if c.get("is_included", True)]
        all_exc = [c for c in processed if not c.get("is_included", True)]

        tot_inc = len(all_inc)
        tot_exc = len(all_exc)

        inc_mapped_all = sum(1 for c in all_inc if c.get("is_mapped"))
        epg_cov_all = round((inc_mapped_all / tot_inc * 100.0), 1) if tot_inc > 0 else 0.0

        global_online = sum(1 for c in all_inc if c.get("link_status") == "online")
        global_offline = sum(1 for c in all_inc if c.get("link_status") == "offline")
        global_unchecked = tot_inc - global_online - global_offline
        global_tested = global_online + global_offline
        global_link_health = round((global_online / global_tested * 100.0), 1) if global_tested > 0 else 0.0

        groups = [c.get("group", "Uncategorized") for c in all_inc if c.get("group")]
        top_groups = Counter(groups).most_common(10)

        global_stats = {
            "total_channels": tot_all,
            "total_included": tot_inc,
            "total_excluded": tot_exc,
            "epg_coverage_included_pct": epg_cov_all,
            "link_online_count": global_online,
            "link_offline_count": global_offline,
            "link_unchecked_count": global_unchecked,
            "link_health_pct": global_link_health,
            "top_groups": top_groups,
        }

        if epg_sources is None:
            from backend.core.source_repository import SourceRepository
            source_repo = SourceRepository()
            db_epg_sources = source_repo.get_all_epg_sources()
            configured_epg_sources = db_epg_sources if db_epg_sources else (getattr(config, "epg_sources", []) if config else [])
        else:
            configured_epg_sources = epg_sources

        if latest_history is None:
            from backend.core.history import SQLiteHistoryRepository
            latest_history = SQLiteHistoryRepository().get_latest()

        last_epg_map: Dict[str, Any] = {}
        is_turbo_run = False
        if latest_history:
            is_turbo_run = getattr(latest_history, "is_turbo", False)
            for es in getattr(latest_history, "epg_stats", []):
                last_epg_map[es.source_name] = es

        if epg_index is None or raw_epg is None:
            db_service = RawDatabaseService(data_dir=settings.data_dir, temp_dir=settings.temp_dir)
            if epg_index is None:
                epg_index = db_service.load_existing_epg_index()
            if raw_epg is None:
                raw_epg = db_service.load_existing_raw_epg()


        epg_stats: List[Dict[str, Any]] = []
        for epg_cfg in configured_epg_sources:
            src_name = epg_cfg.name
            is_enabled = getattr(epg_cfg, "enabled", True)
            prefix = f"{src_name}::"
            total_epg_channels = sum(1 for k in epg_index.keys() if k.startswith(prefix))

            mapped_m3u_channels = sum(
                1 for c in all_inc
                if c.get("is_mapped") and c.get("epg_id", "").startswith(prefix)
            )

            utilization_pct = round((mapped_m3u_channels / total_epg_channels * 100.0), 1) if total_epg_channels > 0 else 0.0

            total_programmes = 0
            programme_starts: List[str] = []
            for k, progs in raw_epg.items():
                if k.startswith(prefix) and isinstance(progs, list):
                    total_programmes += len(progs)
                    for p in progs:
                        if isinstance(p, dict) and p.get("s"):
                            programme_starts.append(p["s"])

            coverage_days = 0
            if programme_starts:
                parsed_dates = [XMLTVParser.parse_date(s) for s in programme_starts if XMLTVParser.parse_date(s)]
                if parsed_dates:
                    min_date = min(parsed_dates)
                    max_date = max(parsed_dates)
                    coverage_days = max(1, (max_date - min_date).days + 1)

            stat_item = last_epg_map.get(src_name)
            last_sync_programmes = stat_item.programmes if stat_item else total_programmes
            last_sync_duration_s = stat_item.duration_s if stat_item else 0.0
            is_turbo = (stat_item.engine == "pro") if stat_item else is_turbo_run
            slow_sync_warning = bool(last_sync_duration_s > 30.0 and not is_turbo)

            epg_stats.append({
                "name": src_name,
                "enabled": is_enabled,
                "status": "ACTIVE" if is_enabled else "DISABLED",
                "total_epg_channels": total_epg_channels,
                "mapped_m3u_channels": mapped_m3u_channels,
                "utilization_pct": utilization_pct,
                "total_programmes": total_programmes,
                "coverage_days": f"{coverage_days} Days" if coverage_days > 0 else "0 Days",
                "last_sync_programmes": last_sync_programmes,
                "last_sync_duration_s": last_sync_duration_s,
                "is_turbo": is_turbo,
                "slow_sync_warning": slow_sync_warning,
            })

        return sources_stats, global_stats, epg_stats
