"""Acquisition services for M3U playlists and XMLTV EPG guides extraction."""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

from backend.config.models import Source, EPGSource
from backend.core.parsers import M3UParser, XMLTVParser
from backend.core.downloader import Downloader
from backend.core.notifier import Notifier
from backend.core.utils import StreamUtils


def _dispatch_source_alert(
    notifier: Notifier,
    event_name: str,
    title_icon: str,
    source_type: str,
    event_type: str,
    source_name: str,
    url: str,
    severity: str,
) -> None:
    """Dispatches a standardized acquisition alert event to Notifier."""
    title = f"{title_icon} Pluvira: {source_type} Source {event_type}"
    if event_type == "Empty/Malformed":
        body = f"{source_type} {'playlist' if source_type == 'M3U' else 'guide'} for source '{source_name}' parsed 0 channels.\nURL: {url}"
    else:
        body = f"Failed to download {source_type} source '{source_name}'.\nURL: {url}"

    notifier.dispatch_event(
        event_name=event_name,
        title=title,
        body=body,
        severity=severity,
    )


class PlaylistAcquisitionService:
    """Service handling download and parsing of IPTV M3U playlist sources."""

    @staticmethod
    def process_source(
        source: Source, temp_dir: Path, global_user_agent: str, notifier: Notifier
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Downloads and parses an M3U playlist source.

        Args:
            source (Source): Source configuration instance.
            temp_dir (Path): Temporary RAM disk path.
            global_user_agent (str): Default User-Agent fallback.
            notifier (Notifier): Notifier instance.

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Extracted raw channel items and acquisition result map.
        """
        logging.info(f"Extracting M3U source '{source.name}'...")
        start_time = time.perf_counter()
        ua = StreamUtils.resolve_user_agent("", "", global_user_agent)
        m3u_tmp = temp_dir / f"{source.name}.m3u"

        raw_channels: List[Dict[str, Any]] = []

        if Downloader.download(source.m3u_url, m3u_tmp, ua):
            channels, errors = M3UParser.parse(str(m3u_tmp), [])
            if errors:
                logging.warning(f"M3U source '{source.name}' encountered {len(errors)} parsing errors.")
                notifier.dispatch_event(
                    event_name="m3u_parsing_error",
                    title="⚠️ Pluvira: M3U Parsing Error",
                    body=f"Parsing issues in source '{source.name}':\n" + "\n".join(errors[:5]),
                    severity="warning",
                )

            duration_s = round(time.perf_counter() - start_time, 2)
            if not channels:
                result = {"type": "m3u", "status": "empty_malformed", "count": 0, "duration_s": duration_s}
                _dispatch_source_alert(
                    notifier, "source_empty_malformed", "⚠️", "M3U", "Empty/Malformed", source.name, source.m3u_url, "warning"
                )
            else:
                result = {"type": "m3u", "status": "success", "count": len(channels), "duration_s": duration_s}

            for ch in channels:
                raw_channels.append({
                    "s": source.name,
                    "n": ch.get("n", ""),
                    "u": ch.get("u", ""),
                    "g": ch.get("g", ""),
                    "l": ch.get("l", ""),
                    "i": ch.get("i", ""),
                    "x": ch.get("x", ""),
                })
            logging.info(f"Extracted {len(channels)} channels from '{source.name}'.")
        else:
            duration_s = round(time.perf_counter() - start_time, 2)
            logging.error(f"Failed to download M3U source '{source.name}'.")
            result = {"type": "m3u", "status": "download_failed", "count": 0, "duration_s": duration_s}
            _dispatch_source_alert(
                notifier, "source_download_failure", "🔴", "M3U", "Download Failed", source.name, source.m3u_url, "critical"
            )

        return raw_channels, result


class EPGAcquisitionService:
    """Service handling download, decompression, and streaming XMLTV EPG guides parsing."""

    @staticmethod
    def process_epg_source(
        epg_source: EPGSource,
        temp_dir: Path,
        global_user_agent: str,
        retention_days: int,
        epg_index: Dict[str, str],
        raw_epg: Dict[str, Any],
        notifier: Notifier,
    ) -> Dict[str, Any]:
        """Downloads, decompresses, and parses an XMLTV guide source.

        Args:
            epg_source (EPGSource): EPG guide source configuration.
            temp_dir (Path): Temporary RAM disk path.
            global_user_agent (str): Default User-Agent fallback.
            retention_days (int): Retention days limit for programme schedules.
            epg_index (Dict[str, str]): EPG index map to populate.
            raw_epg (Dict[str, Any]): Raw EPG schedules map to populate.
            notifier (Notifier): Notifier instance.

        Returns:
            Dict[str, Any]: Acquisition result map.
        """
        logging.info(f"Extracting EPG source '{epg_source.name}'...")
        start_time = time.perf_counter()
        from backend.core.pro_bridge import ProBridge
        engine = "pro" if ProBridge.is_available() else "core"
        epg_ua = getattr(epg_source, "user_agent", "") or ""
        ua = StreamUtils.resolve_user_agent("", epg_ua, global_user_agent)
        url = epg_source.url
        epg_tmp = temp_dir / f"{epg_source.name}_epg.xml"
        dest = epg_tmp.with_suffix(".xml.gz") if url.endswith(".gz") else epg_tmp

        if Downloader.download(url, dest, ua):
            if url.endswith(".gz"):
                Downloader.decompress_gzip(dest, epg_tmp)

            now_utc = datetime.now(timezone.utc)
            max_date = now_utc + timedelta(days=retention_days or 7)
            min_date = now_utc - timedelta(days=1)

            channels_before = len(epg_index)
            programmes_count = 0
            try:
                for elem in XMLTVParser.iter_elements(str(epg_tmp), "channel"):
                    ch_id = elem.get("id")
                    if ch_id:
                        namespaced_id = f"{epg_source.name}::{ch_id}"
                        name = XMLTVParser.get_child_text(elem, "display-name")
                        epg_index[namespaced_id] = name or ch_id

                for elem in XMLTVParser.iter_elements(str(epg_tmp), "programme"):
                    ch_id = elem.get("channel")
                    start, stop = elem.get("start"), elem.get("stop")
                    if ch_id and start and stop:
                        namespaced_id = f"{epg_source.name}::{ch_id}"
                        dt_s = XMLTVParser.parse_date(start)
                        dt_e = XMLTVParser.parse_date(stop)
                        if dt_s and dt_e and min_date <= dt_e <= max_date:
                            if namespaced_id not in raw_epg:
                                raw_epg[namespaced_id] = []
                            raw_epg[namespaced_id].append({
                                "s": start,
                                "e": stop,
                                "t": XMLTVParser.get_child_text(elem, "title"),
                                "d": XMLTVParser.get_child_text(elem, "desc"),
                            })
                            programmes_count += 1
            except Exception as pe:
                logging.error(f"XMLTV parsing failed for '{epg_source.name}': {pe}")
                notifier.dispatch_event(
                    event_name="xmltv_parsing_error",
                    title="⚠️ Pluvira: XMLTV Parsing Error",
                    body=f"XMLTV parsing error for '{epg_source.name}':\n{pe}",
                    severity="warning",
                )

            channels_extracted = len(epg_index) - channels_before
            duration_s = round(time.perf_counter() - start_time, 2)
            if channels_extracted == 0 and programmes_count == 0:
                result = {"type": "epg", "status": "empty_malformed", "count": 0, "programmes": 0, "duration_s": duration_s, "engine": engine}
                _dispatch_source_alert(
                    notifier, "source_empty_malformed", "⚠️", "EPG", "Empty/Malformed", epg_source.name, url, "warning"
                )
            else:
                result = {"type": "epg", "status": "success", "count": channels_extracted, "programmes": programmes_count, "duration_s": duration_s, "engine": engine}
        else:
            duration_s = round(time.perf_counter() - start_time, 2)
            logging.error(f"Failed to download EPG source '{epg_source.name}'.")
            result = {"type": "epg", "status": "download_failed", "count": 0, "programmes": 0, "duration_s": duration_s, "engine": engine}
            _dispatch_source_alert(
                notifier, "source_download_failure", "🔴", "EPG", "Download Failed", epg_source.name, url, "critical"
            )

        return result
