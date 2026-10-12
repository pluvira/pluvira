"""Merge service layer encapsulating business logic for channel deduplication and failover merges."""

from typing import List, Dict, Any, Optional, Union
from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import ChannelMerge, StreamRef
from backend.core.processor import DataProcessor
from backend.core.deduplication_engine import DeduplicationEngine
from backend.core.exceptions import EntityNotFoundError
from backend.core.pro_bridge import ProBridge
from backend.core.channel_merge_repository import ChannelMergeRepository


class MergeService:
    """Service handling on-demand channel deduplication scanning, merge application, and deletions."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        processor: Optional[DataProcessor] = None,
        dedup_service: Optional[DeduplicationEngine] = None,
        merge_repo: Optional[ChannelMergeRepository] = None,
    ) -> None:
        """Initializes merge service.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
            processor (Optional[DataProcessor]): Override data processor instance.
            dedup_service (Optional[DeduplicationEngine]): Override deduplication engine instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.processor = processor or DataProcessor()
        self.dedup_service = dedup_service or DeduplicationEngine()
        self.merge_repo = merge_repo or ChannelMergeRepository()

    def get_duplicate_clusters(self, similarity_threshold: float = 0.80) -> List[Dict[str, Any]]:
        """Scans processed channels on-demand and returns duplicate candidate clusters enriched with merge status.

        Args:
            similarity_threshold (float): Fuzzy similarity threshold ratio.

        Returns:
            List[Dict[str, Any]]: List of cluster objects containing is_merged, status, and merged_details.
        """
        config = self.config_handler.load_config()

        channels = self.processor.get_processed_channels(config=config, include_backups=True)

        clusters = None
        if ProBridge.is_available():
            pro_res = ProBridge.execute_sync(
                "find-duplicate-clusters",
                payload={"channels": channels, "similarity_threshold": similarity_threshold},
            )
            if pro_res and isinstance(pro_res, dict):
                res_obj = pro_res.get("result") if isinstance(pro_res.get("result"), dict) else pro_res
                cand_clusters = res_obj.get("clusters")
                if isinstance(cand_clusters, list) and all(isinstance(c, dict) for c in cand_clusters):
                    clusters = cand_clusters

        if clusters is None:
            clusters = self.dedup_service.find_duplicate_clusters(
                channels, similarity_threshold=similarity_threshold
            )

        merged_map = self.merge_repo.get_all()

        merged_primary_keys = {}
        merged_primary_urls = {}
        for name, m in merged_map.items():
            if m and m.primary_stream and m.primary_stream.url:
                p_src = getattr(m.primary_stream, "source", "") or ""
                merged_primary_keys[(m.primary_stream.url, p_src)] = name
                merged_primary_urls[m.primary_stream.url] = name

        for cluster in clusters:
            c_name = cluster.get("canonical_name", "")
            cand_keys = {
                (c.get("url") or c.get("original_url", ""), c.get("source", ""))
                for c in cluster.get("candidates", [])
                if c.get("url") or c.get("original_url")
            }

            match_name = None
            if c_name in merged_map:
                match_name = c_name
            else:
                for key in cand_keys:
                    if key in merged_primary_keys:
                        match_name = merged_primary_keys[key]
                        break
                if not match_name:
                    for url, _ in cand_keys:
                        if url in merged_primary_urls:
                            match_name = merged_primary_urls[url]
                            break

            is_merged = match_name is not None
            cluster["is_merged"] = is_merged
            cluster["status"] = "merged" if is_merged else "suggested"
            cluster["merged_details"] = (
                merged_map[match_name].model_dump()
                if match_name and match_name in merged_map
                else None
            )

        return clusters

    @staticmethod
    def _build_channel_merge_entry(
        master_name: str,
        primary_stream: Union[StreamRef, Dict[str, Any]],
        backup_streams: List[Union[StreamRef, Dict[str, Any]]],
        logo: str = "",
        group: str = "",
        epg_id: str = "",
    ) -> ChannelMerge:
        """Helper to build and validate a ChannelMerge domain model."""
        primary = (
            primary_stream
            if isinstance(primary_stream, StreamRef)
            else StreamRef.model_validate(primary_stream)
        )
        backups = [
            b if isinstance(b, StreamRef) else StreamRef.model_validate(b)
            for b in backup_streams
        ]
        return ChannelMerge(
            name=master_name,
            logo=logo or "",
            group=group or "",
            epg_id=epg_id or "",
            primary_stream=primary,
            backup_streams=backups,
        )

    def apply_channel_merge(
        self,
        master_name: str,
        primary_stream: StreamRef,
        backup_streams: List[StreamRef],
        logo: str = "",
        group: str = "",
        epg_id: str = "",
    ) -> None:
        """Persists a new or updated ChannelMerge configuration."""
        merge_entry = self._build_channel_merge_entry(
            master_name, primary_stream, backup_streams, logo, group, epg_id
        )

        self.merge_repo.save_merge(merge_entry, master_name=master_name)

    def delete_channel_merge(self, master_name: str) -> None:
        """Removes a ChannelMerge configuration by master name."""
        if self.merge_repo.delete_merge(master_name):
            return

        raise EntityNotFoundError(f"Merge configuration for '{master_name}' not found.")

    def bulk_apply_channel_merges(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Persists multiple ChannelMerge configurations in a single atomic transaction."""
        applied_count = 0
        for item in items:
            master_name = item.get("master_name")
            if not master_name:
                continue

            merge_entry = self._build_channel_merge_entry(
                master_name=master_name,
                primary_stream=item.get("primary_stream"),
                backup_streams=item.get("backup_streams", []),
                logo=item.get("logo", ""),
                group=item.get("group", ""),
                epg_id=item.get("epg_id", ""),
            )
            self.merge_repo.save_merge(merge_entry, master_name=master_name)
            applied_count += 1

        return {"message": "Bulk merge applied successfully", "count": applied_count}

    def bulk_delete_channel_merges(self, master_names: List[str]) -> Dict[str, Any]:
        """Removes multiple ChannelMerge configurations in bulk by master names."""
        deleted_count = self.merge_repo.bulk_delete_merges(master_names)
        return {"message": "Bulk unmerge completed", "count": deleted_count}


    def auto_apply_channel_merges(self, similarity_threshold: float = 0.95) -> Dict[str, Any]:
        """Automatically creates channel merge configurations for high-confidence duplicate clusters."""
        clusters = self.get_duplicate_clusters(similarity_threshold=similarity_threshold)
        merged_count = 0
        existing_merges = self.merge_repo.get_all()

        for cluster in clusters:
            canonical_name = cluster.get("canonical_name", "").strip()
            candidates = cluster.get("candidates", [])

            if not canonical_name or len(candidates) < 2:
                continue

            if canonical_name in existing_merges:
                continue

            p_cand = candidates[0]
            primary_stream = StreamRef(
                url=p_cand.get("url") or p_cand.get("original_url", ""),
                source=p_cand.get("source", "Unknown"),
                user_agent=p_cand.get("user_agent"),
            )

            backup_streams = [
                StreamRef(
                    url=b_cand.get("url") or b_cand.get("original_url", ""),
                    source=b_cand.get("source", "Unknown"),
                    user_agent=b_cand.get("user_agent"),
                )
                for b_cand in candidates[1:]
            ]

            merge_entry = self._build_channel_merge_entry(
                master_name=canonical_name,
                primary_stream=primary_stream,
                backup_streams=backup_streams,
                logo=p_cand.get("logo", ""),
                group=p_cand.get("group", ""),
                epg_id=p_cand.get("epg_id", ""),
            )
            self.merge_repo.save_merge(merge_entry, master_name=canonical_name)
            merged_count += 1

        return {"message": "Auto-merge completed", "merged_count": merged_count}



    def get_merge_stats(self, similarity_threshold: float = 0.80) -> Dict[str, Any]:
        """Calculates aggregate metrics for the merge system.

        Args:
            similarity_threshold (float): Fuzzy similarity threshold ratio.

        Returns:
            Dict[str, Any]: Metrics dictionary containing clusters, merged channels, and backup streams.
        """
        clusters = self.get_duplicate_clusters(similarity_threshold=similarity_threshold)
        all_merges = self.merge_repo.get_all()

        total_clusters_detected = len(clusters)
        total_merged_channels = len(all_merges)

        merged_keys = set(all_merges.keys())
        unmerged = sum(1 for c in clusters if c.get("canonical_name") not in merged_keys)
        total_backup_streams = sum(
            len(m.backup_streams) for m in all_merges.values() if m and m.backup_streams
        )

        return {
            "total_clusters_detected": total_clusters_detected,
            "total_merged_channels": total_merged_channels,
            "total_unmerged_clusters": unmerged,
            "total_backup_streams": total_backup_streams,
        }
