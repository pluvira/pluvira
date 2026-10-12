"""Channel service layer encapsulating business logic and config persistence for channels."""

from typing import List, Dict, Any, Optional
from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import RewriteRule
from backend.core.processor import DataProcessor
from backend.core.individual_rewrite_repository import IndividualRewriteRepository
from backend.core.epg_override_repository import EpgOverrideRepository
from backend.core.source_filter_repository import SourceFilterRepository


class ChannelService:
    """Service handling channel retrieval, metadata rewrites, EPG overrides, and bulk actions."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        processor: Optional[DataProcessor] = None,
        rewrite_repo: Optional[IndividualRewriteRepository] = None,
        epg_override_repo: Optional[EpgOverrideRepository] = None,
        source_filter_repo: Optional[SourceFilterRepository] = None,
    ) -> None:
        """Initializes channel service with configuration handler, processor, and rewrite repository.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
            processor (Optional[DataProcessor]): Override data processor instance.
            rewrite_repo (Optional[IndividualRewriteRepository]): Override individual rewrite repository instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.processor = processor or DataProcessor()
        self.rewrite_repo = rewrite_repo or getattr(self.processor, "rewrite_repo", None) or IndividualRewriteRepository()
        self.epg_override_repo = (
            epg_override_repo
            or getattr(self.processor, "epg_override_repo", None)
            or EpgOverrideRepository()
        )
        self.source_filter_repo = (
            source_filter_repo
            or getattr(self.processor, "source_filter_repo", None)
            or SourceFilterRepository()
        )

    def get_processed_channels(
        self,
        search: Optional[str] = None,
        source: Optional[str] = None,
        group: Optional[str] = None,
        is_included: Optional[bool] = None,
        is_mapped: Optional[bool] = None,
        link_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Retrieves processed channels with filtering and pagination parameters.

        Returns:
            Dict[str, Any]: Dictionary with total count, limit, offset, and paginated items list.
        """
        channels = self.processor.get_processed_channels()

        if search:
            q = search.lower()
            channels = [c for c in channels if q in c.get("name", "").lower()]

        if source:
            channels = [c for c in channels if c.get("source") == source]

        if group:
            channels = [c for c in channels if c.get("group") == group]

        if is_included is not None:
            channels = [c for c in channels if c.get("is_included") == is_included]

        if is_mapped is not None:
            channels = [c for c in channels if c.get("is_mapped") == is_mapped]

        if link_status:
            st = link_status.lower()
            channels = [c for c in channels if c.get("link_status", "").lower() == st]

        total_count = len(channels)
        paginated_items = channels[offset : offset + limit]

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "items": paginated_items,
        }

    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single channel by its unique MD5 hash identifier.

        Args:
            channel_id (str): Channel MD5 hash.

        Returns:
            Optional[Dict[str, Any]]: Channel dictionary model if found.
        """
        channels = self.processor.get_processed_channels(include_backups=True)
        return next((ch for ch in channels if ch.get("id") == channel_id), None)

    def update_individual_rewrite(
        self, original_url: str, field: str, original_val: str, new_val: str
    ) -> None:
        """Updates or removes an individual channel attribute rewrite rule in SQLite repository.

        Args:
            original_url (str): Channel immutable original_url key.
            field (str): Attribute field name.
            original_val (str): Original raw attribute value.
            new_val (str): New value string to apply.
        """
        val_clean = new_val.strip()
        if val_clean and val_clean != original_val:
            self.rewrite_repo.set_rule(original_url, field, val_clean, mode="replace")
        else:
            self.rewrite_repo.delete_rule(original_url, field)

    def update_epg_mapping(
        self, channel_name: str, source_name: str, epg_id: str, is_global: bool = False
    ) -> None:
        """Updates manual EPG mapping override for a channel globally or per-source.

        Args:
            channel_name (str): Target channel display name.
            source_name (str): IPTV source provider name.
            epg_id (str): Namespaced EPG channel ID.
            is_global (bool): Apply override globally across all sources.
        """
        src = None if is_global else source_name
        self.epg_override_repo.set_override(channel_name, epg_id, source_name=src)

    def bulk_set_inclusion(self, channel_items: List[Dict[str, Any]], is_included: bool) -> int:
        """Updates channel inclusion/exclusion status in bulk for source settings.

        Args:
            channel_items (List[Dict[str, Any]]): List of channel item models.
            is_included (bool): Target inclusion status boolean.

        Returns:
            int: Number of items processed.
        """
        if not channel_items:
            return 0

        grouped_by_source: Dict[str, List[str]] = {}
        count = 0

        for item in channel_items:
            source_name = item.get("source")
            orig_data = item.get("original_data") or {}
            ch_name = (
                orig_data.get("name")
                if isinstance(orig_data, dict) and orig_data.get("name")
                else item.get("name")
            )
            if not source_name or not ch_name:
                continue

            grouped_by_source.setdefault(source_name, []).append(ch_name)
            count += 1

        filter_type = "allow" if is_included else "deny"
        for source_name, ch_names in grouped_by_source.items():
            self.source_filter_repo.bulk_set_filters(source_name, ch_names, filter_type)

        return count

    def _bulk_set_individual_rewrite_field(self, original_urls: List[str], field: str, value: str) -> int:
        """Helper to assign an attribute in bulk via individual rewrite rules in SQLite repository."""
        if not original_urls:
            return 0

        val_str = value.strip()
        if val_str:
            self.rewrite_repo.bulk_set_field(original_urls, field, val_str, mode="replace")
        else:
            for u in original_urls:
                self.rewrite_repo.delete_rule(u, field)

        return len(original_urls)

    def bulk_set_group(self, original_urls: List[str], group: str) -> int:
        """Assigns channel group in bulk via individual rewrite rules."""
        return self._bulk_set_individual_rewrite_field(original_urls, "group", group)

    def bulk_set_user_agent(self, original_urls: List[str], user_agent: str) -> int:
        """Assigns channel User-Agent in bulk via individual rewrite rules."""
        return self._bulk_set_individual_rewrite_field(original_urls, "user_agent", user_agent)

    def bulk_reset_rewrites(self, original_urls: List[str]) -> int:
        """Clears individual rewrite rules in bulk for target channel original_urls from SQLite repository.

        Args:
            original_urls (List[str]): Target original_url keys.

        Returns:
            int: Count of channels reset.
        """
        if not original_urls:
            return 0

        self.rewrite_repo.bulk_delete_by_urls(original_urls)
        return len(original_urls)



    def _get_required_channel_by_id(self, channel_id: str) -> Dict[str, Any]:
        """Retrieves channel by ID or raises EntityNotFoundError if missing."""
        ch = self.get_channel_by_id(channel_id)
        if not ch:
            from backend.core.exceptions import EntityNotFoundError
            raise EntityNotFoundError(f"Channel with ID '{channel_id}' not found.")
        return ch

    def update_rewrite_by_channel_id(
        self,
        channel_id: str,
        field: str,
        new_val: str,
        original_url: Optional[str] = None,
        original_val: Optional[str] = None,
    ) -> None:
        """Updates individual rewrite rule targeting a channel by its unique ID."""
        ch = self._get_required_channel_by_id(channel_id)
        target_url = original_url or ch.get("original_url", "")
        target_val = original_val or ch.get(field, "")
        self.update_individual_rewrite(target_url, field, target_val, new_val)

    def update_epg_mapping_by_channel_id(
        self,
        channel_id: str,
        epg_id: str,
        channel_name: Optional[str] = None,
        source_name: Optional[str] = None,
        is_global: bool = False,
    ) -> None:
        """Updates EPG mapping override targeting a channel by its unique ID."""
        ch = self._get_required_channel_by_id(channel_id)
        target_name = channel_name or ch.get("name", "")
        target_source = source_name or ch.get("source", "")
        self.update_epg_mapping(target_name, target_source, epg_id, is_global)

    def auto_assign_epg(
        self,
        scope: str = "curated",
        playlist_id: str = "default",
        similarity_threshold: float = 0.85,
        overwrite_existing: bool = False,
        source: Optional[str] = None,
        only_unmapped: bool = True,
    ) -> Dict[str, Any]:
        """Automatically assigns EPG guides to channels enforcing Freemium BSL 1.1 limits.

        Args:
            scope (str): Scope of channels ('curated' for My List, 'all' for full catalog).
            playlist_id (str): Target curated playlist identifier.
            similarity_threshold (float): Minimum similarity threshold (0.50 to 1.00).
            overwrite_existing (bool): Whether to overwrite existing manual EPG mappings.
            source (Optional[str]): Optional source name filter.
            only_unmapped (bool): If True, only targets channels currently unmapped to EPG.

        Returns:
            Dict[str, Any]: Dictionary with execution metrics and applied overrides.
        """
        from backend.config.settings import settings
        from backend.core.license_thresholds import LicenseThresholdManager
        from backend.core.personal_repository import PersonalPlaylistRepository
        from backend.core.raw_database import RawDatabaseService
        from backend.core.merger import ChannelMerger
        from backend.core.pro_bridge import ProBridge

        is_unmapped_target = not overwrite_existing if overwrite_existing else only_unmapped

        p_channels: List[Dict[str, Any]] = []
        if scope.lower() == "curated":
            personal_repo = PersonalPlaylistRepository(data_dir=settings.data_dir)
            p_channels = personal_repo.get_channels(playlist_id=playlist_id)
            if p_channels:
                candidate_channels: List[Dict[str, Any]] = []
                for pch in p_channels:
                    ch_source = ""
                    ch_url = ""
                    if pch.get("slots"):
                        ch_source = pch["slots"][0].get("source", "")
                        ch_url = pch["slots"][0].get("url", "")
                    candidate_channels.append({
                        "id": pch.get("id"),
                        "name": pch.get("name", ""),
                        "source": ch_source,
                        "url": ch_url,
                        "epg_id": pch.get("epg_id") or "",
                    })
            else:
                all_channels = self.processor.get_processed_channels()
                candidate_channels = [
                    ch for ch in all_channels
                    if ch.get("is_bookmarked") or playlist_id in (ch.get("bookmarked_playlist_ids") or [])
                ]
        else:
            candidate_channels = self.processor.get_processed_channels()

        if source:
            candidate_channels = [c for c in candidate_channels if c.get("source") == source]

        evaluated_count = len(candidate_channels)

        LicenseThresholdManager.validate_auto_map_epg(
            scope=scope,
            similarity_threshold=similarity_threshold,
            channel_count=evaluated_count,
        )

        raw_db = RawDatabaseService(data_dir=settings.data_dir, temp_dir=settings.temp_dir)
        epg_index = raw_db.load_existing_epg_index()

        applied_overrides: List[Dict[str, Any]] = []
        is_pro = ProBridge.is_available()

        matches: Optional[List[Dict[str, Any]]] = None
        if is_pro:
            try:
                epg_channels_list = [
                    {"id": k, "name": v, "raw_id": k.split("::", 1)[1] if "::" in k else k}
                    for k, v in epg_index.items()
                ]
                pro_res = ProBridge.execute_sync(
                    "auto-map-epg",
                    payload={
                        "channels": candidate_channels,
                        "epg_channels": epg_channels_list,
                        "similarity_threshold": similarity_threshold,
                        "only_unmapped": is_unmapped_target,
                    },
                )
                if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
                    matches = pro_res.get("result", {}).get("matches")
            except Exception:
                matches = None

        if matches is None:
            merger = getattr(self.processor, "merger", None) or ChannelMerger()
            matches = merger.batch_match_epg(
                channels=candidate_channels,
                epg_channels_index=epg_index,
                similarity_threshold=similarity_threshold,
                only_unmapped=is_unmapped_target,
                source_filter=source,
            )

        for m in matches:
            ch_name = m.get("channel_name", "")
            ch_source = m.get("source_name", "")
            epg_id = m.get("epg_id", "")
            if ch_name and epg_id:
                self.epg_override_repo.set_override(
                    channel_name=ch_name,
                    epg_id=epg_id,
                    source_name=ch_source if ch_source else None,
                )
                applied_overrides.append({
                    "channel_name": ch_name,
                    "source_name": ch_source,
                    "epg_id": epg_id,
                })

        if scope.lower() == "curated" and applied_overrides and p_channels:
            personal_repo = PersonalPlaylistRepository(data_dir=settings.data_dir)
            for o in applied_overrides:
                for pch in p_channels:
                    if pch.get("name") == o["channel_name"]:
                        personal_repo.update_channel_metadata(
                            channel_id=pch["id"],
                            name=pch["name"],
                            logo=pch.get("logo", ""),
                            epg_id=o["epg_id"],
                            group_name=pch.get("group", ""),
                            custom_order=pch.get("custom_order", 0),
                            is_pinned=pch.get("is_pinned", False),
                        )

        mapped_count = len(applied_overrides)
        skipped_count = max(0, evaluated_count - mapped_count)

        return {
            "success": True,
            "scope": scope,
            "total_evaluated": evaluated_count,
            "mapped_count": mapped_count,
            "matched_count": mapped_count,
            "skipped_count": skipped_count,
            "is_pro": is_pro,
            "message": f"Successfully mapped {mapped_count} channel(s) automatically.",
            "applied_overrides": applied_overrides,
        }
