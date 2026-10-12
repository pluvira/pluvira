"""Basic exact-string equality deduplication engine for Pluvira Core."""

import hashlib
from typing import List, Dict, Any
from backend.core.merger import ChannelMerger


class DeduplicationEngine:
    """Exact normalized string equality comparison for duplicate candidate channels in Pluvira Core edition."""

    def __init__(self) -> None:
        """Initializes deduplication service with channel merger instance."""
        self.merger = ChannelMerger()

    def normalize_string(self, text: str) -> str:
        """Normalizes channel name by stripping quality tags, lowercasing, and collapsing whitespace.

        Args:
            text (str): Input channel name.

        Returns:
            str: Cleaned and normalized string.
        """
        if not text:
            return ""
        cleaned = self.merger.normalize_name(text, level=1)
        return " ".join(cleaned.lower().split())

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculates exact normalized string equality score (1.0 or 0.0) between channel names.

        Args:
            name1 (str): First channel name.
            name2 (str): Second channel name.

        Returns:
            float: 1.0 if normalized strings match exactly, 0.0 otherwise.
        """
        norm1 = self.normalize_string(name1)
        norm2 = self.normalize_string(name2)

        if not norm1 or not norm2:
            return 0.0

        return 1.0 if norm1 == norm2 else 0.0

    def find_duplicate_clusters(
        self, channels: List[Dict[str, Any]], similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """Groups channels into duplicate candidate clusters based on fuzzy name similarity.

        Args:
            channels (List[Dict[str, Any]]): Processed channel models list.
            similarity_threshold (float): Ignored in Core exact matching engine.

        Returns:
            List[Dict[str, Any]]: List of cluster objects containing canonical_name and candidates.
        """
        clusters: List[Dict[str, Any]] = []
        assigned_channel_ids = set()

        sorted_channels = sorted(channels, key=lambda c: len(c.get("name", "")))

        for i, ch in enumerate(sorted_channels):
            ch_id = ch.get("id") or ch.get("original_url")
            if ch_id in assigned_channel_ids:
                continue

            ch_name = ch.get("name", "").strip()
            if not ch_name:
                continue

            current_cluster_candidates = [ch]

            for j, other in enumerate(sorted_channels):
                if i == j:
                    continue
                other_id = other.get("id") or other.get("original_url")
                if other_id in assigned_channel_ids:
                    continue

                other_name = other.get("name", "").strip()
                if not other_name:
                    continue

                if self.calculate_similarity(ch_name, other_name) == 1.0:
                    current_cluster_candidates.append(other)

            if len(current_cluster_candidates) > 1:
                formatted_candidates = []
                for c in current_cluster_candidates:
                    c_id = c.get("id") or c.get("original_url")
                    assigned_channel_ids.add(c_id)

                    c_copy = dict(c)
                    c_url = c.get("url") or c.get("original_url", "")
                    c_src = c.get("source", "Unknown")
                    c_copy["candidate_id"] = hashlib.md5(f"{c_url}{c_src}".encode()).hexdigest()
                    formatted_candidates.append(c_copy)

                cluster_key = hashlib.md5(f"{ch_name}_{len(clusters)}".encode()).hexdigest()[:8]
                clusters.append({
                    "cluster_id": f"cluster_{cluster_key}",
                    "canonical_name": ch_name,
                    "candidates": formatted_candidates,
                })

        return clusters


# Backward compatibility alias
DeduplicationService = DeduplicationEngine
