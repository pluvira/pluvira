"""EPG service layer encapsulating business logic for programme schedule queries and date filtering."""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta

from backend.config.settings import settings
from backend.core.exceptions import ValidationDomainError
from backend.core.processor import DataProcessor
from backend.core.parsers import XMLTVParser
from backend.core.raw_database import RawDatabaseService


class EpgService:
    """Service handling EPG programme schedule retrieval and date range filtering."""

    def __init__(
        self,
        processor: Optional[DataProcessor] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        """Initializes EPG service with data processor instance and data directory.

        Args:
            processor (Optional[DataProcessor]): Override data processor instance.
            data_dir (Optional[Path]): Override persistent data directory.
        """
        self.processor = processor or DataProcessor()
        self.data_dir = data_dir or settings.data_dir

    def _load_epg_index(self) -> Dict[str, str]:
        """Loads epg_index from SQLite or JSON fallback."""
        db_service = RawDatabaseService(data_dir=self.data_dir)
        return db_service.load_existing_epg_index()

    def get_epg_channels(
        self,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves indexed EPG channels with optional source filtering and text search.

        Args:
            source (Optional[str]): Optional EPG guide source name filter.
            search (Optional[str]): Optional partial search query matching name or raw ID.
            limit (int): Maximum items to return (default 100, max 500).

        Returns:
            List[Dict[str, Any]]: List of channel items with id, raw_id, name, source.
        """
        epg_index = self._load_epg_index()
        if not epg_index:
            return []

        search_query = search.strip().lower() if search else None
        target_source = source.strip().lower() if source else None
        safe_limit = max(1, min(limit, 500))

        channels: List[Dict[str, Any]] = []
        for namespaced_id, name in epg_index.items():
            if "::" in namespaced_id:
                src_name, raw_id = namespaced_id.split("::", 1)
            else:
                src_name, raw_id = "Unknown", namespaced_id

            if target_source and src_name.lower() != target_source:
                continue

            if search_query:
                display_name = (name or "").lower()
                raw_lower = raw_id.lower()
                if search_query not in display_name and search_query not in raw_lower:
                    continue

            channels.append({
                "id": namespaced_id,
                "raw_id": raw_id,
                "name": name or raw_id,
                "source": src_name,
            })

            if len(channels) >= safe_limit:
                break

        return channels

    def get_programmes(
        self,
        ids: Union[str, List[str]],
        date: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves and filters EPG programme schedules for target channel IDs."""
        if isinstance(ids, str):
            target_ids = [i.strip() for i in ids.split(",") if i.strip()]
        else:
            target_ids = [i.strip() for i in ids if i and i.strip()]

        if not target_ids:
            return {}

        t_start = time.perf_counter()
        logging.info(
            f"[EPG Service] get_programmes requested for {len(target_ids)} channels "
            f"(date={date}, date_from={date_from}, date_to={date_to})"
        )
        try:
            db_service = RawDatabaseService(data_dir=self.data_dir)
            epg_data = db_service.load_existing_raw_epg(channel_ids=target_ids)
            if not epg_data and hasattr(self.processor, "get_epg_data"):
                epg_data = self.processor.get_epg_data(set(target_ids))

            if not date and not date_from and not date_to:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                total_progs = sum(len(v) for v in epg_data.values())
                logging.info(
                    f"[EPG Service] get_programmes (unfiltered) resolved in {elapsed_ms:.1f}ms: "
                    f"{len(epg_data)} channels matched, {total_progs} programmes."
                )
                return epg_data

            start_bound = None
            end_bound = None

            if date:
                dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                start_bound = dt - timedelta(hours=14)
                end_bound = dt.replace(hour=23, minute=59, second=59) + timedelta(hours=14)
            else:
                if date_from:
                    start_bound = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc) - timedelta(hours=14)
                if date_to:
                    end_bound = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc) + timedelta(hours=14)

            date_parse_cache: Dict[str, Optional[datetime]] = {}

            def get_parsed_utc_date(date_str: str) -> Optional[datetime]:
                if not date_str:
                    return None
                if date_str not in date_parse_cache:
                    dt = XMLTVParser.parse_date(date_str)
                    if not dt:
                        try:
                            clean_str = date_str.replace("Z", "+00:00").strip()
                            if "T" in clean_str or " " in clean_str:
                                dt = datetime.fromisoformat(clean_str)
                        except Exception:
                            dt = None
                    date_parse_cache[date_str] = (
                        dt.astimezone(timezone.utc)
                        if dt and dt.tzinfo
                        else (dt.replace(tzinfo=timezone.utc) if dt else None)
                    )
                return date_parse_cache[date_str]

            filtered_data = {}
            for eid, progs in epg_data.items():
                filtered_progs = []
                for p in progs:
                    p_start_utc = get_parsed_utc_date(p.get("s", ""))
                    p_end_utc = get_parsed_utc_date(p.get("e", ""))

                    if not p_start_utc or not p_end_utc:
                        continue

                    if start_bound and p_end_utc <= start_bound:
                        continue
                    if end_bound and p_start_utc >= end_bound:
                        continue

                    filtered_progs.append(p)

                if filtered_progs:
                    filtered_data[eid] = filtered_progs

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            total_filtered = sum(len(v) for v in filtered_data.values())
            logging.info(
                f"[EPG Service] get_programmes (filtered) completed in {elapsed_ms:.1f}ms: "
                f"{len(filtered_data)} channels, {total_filtered} programmes."
            )
            return filtered_data

        except ValueError as ve:
            raise ValidationDomainError(f"Invalid date format. Use YYYY-MM-DD. Error: {ve}")
