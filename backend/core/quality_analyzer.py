"""Quality analyzer engine for channel processing metrics, conflict detection, and EPG coverage checks."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.config.models import GlobalConfig
from backend.core.parsers import XMLTVParser
from backend.core.notifier import Notifier


class QualityAnalyzer:
    """Analyzes processed channel lists and raw EPG schedules for issues and dispatches warning notifications."""

    @staticmethod
    def analyze_processed_channels(
        processed_list: List[Dict[str, Any]],
        config: GlobalConfig,
        epg_sources_order: List[str],
        duration: float,
    ) -> None:
        """Analyzes processed channel lists and raw EPG schedules for issues and dispatches warning notifications.

        Args:
            processed_list (List[Dict[str, Any]]): Processed channels list.
            config (GlobalConfig): Global configuration instance.
            epg_sources_order (List[str]): Ordered list of enabled EPG source names.
            duration (float): Processing duration in seconds.
        """
        logging.info(f"Pluvira Core processed {len(processed_list)} channels in {duration:.2f}s.")
        notifier = Notifier.from_config(config)
        events = config.get_event_config()

        included = [c for c in processed_list if c.get("is_included")]
        if included:
            unmapped = [c for c in included if not c.get("is_mapped")]
            unmapped_pct = round((len(unmapped) / len(included) * 100.0), 1)
            threshold = events.unmapped_included_threshold_pct
            if unmapped_pct > threshold:
                notifier.dispatch_event(
                    event_name="unmapped_included_warning",
                    title="⚠️ Pluvira: High Unmapped Included Channels",
                    body=f"High percentage of included channels without EPG mapping ({unmapped_pct}%).\nUnmapped: {len(unmapped)}/{len(included)}\nThreshold: {threshold}%",
                    severity="warning",
                )

        seen_urls = {}
        conflicts = []
        name_to_sources = {}
        used_epg_prefixes = set()

        for ch in processed_list:
            name, url = ch.get("name", "").strip(), ch.get("url", "").strip()
            if not name:
                conflicts.append(f"Channel ID '{ch['id']}' has an EMPTY name after rewrites.")
            if not url:
                conflicts.append(f"Channel '{name}' has an EMPTY stream URL after rewrites.")
            elif url in seen_urls:
                conflicts.append(f"URL conflict detected: '{url}' used by both '{seen_urls[url]}' and '{name}'.")
            else:
                seen_urls[url] = name

            if ch.get("is_included"):
                if name:
                    if name not in name_to_sources:
                        name_to_sources[name] = set()
                    name_to_sources[name].add(ch.get("source", "Unknown"))
                if ch.get("is_mapped") and ch.get("epg_id") and "::" in ch["epg_id"]:
                    used_epg_prefixes.add(ch["epg_id"].split("::", 1)[0])

        if conflicts:
            summary = "\n".join(conflicts[:10]) + (f"\n... and {len(conflicts)-10} more." if len(conflicts) > 10 else "")
            notifier.dispatch_event(
                event_name="rewrite_conflict_warning",
                title="⚠️ Pluvira: Rewrite Conflicts Detected",
                body=f"Found {len(conflicts)} conflict(s):\n{summary}",
                severity="warning",
            )

        duplicates = {n: s for n, s in name_to_sources.items() if len(s) > 1}
        if duplicates:
            dup_details = [f"• {n} (Sources: {', '.join(sorted(list(s)))})" for n, s in list(duplicates.items())[:10]]
            body = f"Detected {len(duplicates)} duplicate names:\n" + "\n".join(dup_details) + (f"\n... and {len(duplicates)-10} more." if len(duplicates) > 10 else "")
            notifier.dispatch_event(
                event_name="duplicate_channel_warning",
                title="⚠️ Pluvira: Duplicate Channel Names",
                body=body,
                severity="warning",
            )

        unused_sources = [src for src in epg_sources_order if src not in used_epg_prefixes]
        if unused_sources:
            notifier.dispatch_event(
                event_name="epg_source_unused",
                title="⚠️ Pluvira: Unused EPG Sources",
                body="Enabled but unused EPG sources:\n- " + "\n- ".join(unused_sources),
                severity="warning",
            )

        perf_threshold = events.slow_processing_threshold_s
        if duration > perf_threshold:
            notifier.dispatch_event(
                event_name="slow_processing_warning",
                title="⚠️ Pluvira: Slow Processing Detected",
                body=f"Took {duration:.2f}s (Threshold: {perf_threshold}s).",
                severity="warning",
            )

    @staticmethod
    def check_epg_future_coverage(
        config: GlobalConfig, all_epg: Optional[Dict[str, Any]] = None
    ) -> float:
        """Inspects raw_epg for future programme coverage and dispatches warning if low.

        Args:
            config (GlobalConfig): Global configuration instance.
            all_epg (Optional[Dict[str, Any]]): Pre-loaded raw EPG data.

        Returns:
            float: Hours of future EPG coverage available.
        """

        if all_epg is None:
            from backend.core.raw_database import RawDatabaseService
            all_epg = RawDatabaseService().load_existing_raw_epg()

        if not all_epg:
            return 0.0

        notifier = Notifier.from_config(config)
        events = config.get_event_config()

        max_stop_dt: Optional[datetime] = None
        try:
            for progs in (all_epg or {}).values():
                if isinstance(progs, list):
                    for p in progs:
                        if isinstance(p, dict) and p.get("e"):
                            parsed = XMLTVParser.parse_date(p["e"])
                            if parsed:
                                parsed_utc = parsed.astimezone(timezone.utc)
                                if max_stop_dt is None or parsed_utc > max_stop_dt:
                                    max_stop_dt = parsed_utc

            now_utc = datetime.now(timezone.utc)
            future_hours = 0.0
            if max_stop_dt and max_stop_dt > now_utc:
                future_hours = round((max_stop_dt - now_utc).total_seconds() / 3600.0, 1)

            min_hours = events.min_epg_future_hours

            if future_hours < min_hours:
                notifier.dispatch_event(
                    event_name="epg_expiration_warning",
                    title="⚠️ Pluvira: Low EPG Future Coverage",
                    body=f"EPG future schedule coverage is low ({future_hours} hours available).\nRequired Minimum: {min_hours} hours.",
                    severity="warning",
                )

            return future_hours
        except Exception as e:
            logging.error(f"Failed to check EPG future coverage: {e}")
            return 0.0


# Backward compatibility alias
QualityAnalyzerService = QualityAnalyzer
