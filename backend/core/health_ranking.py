"""Health ranking, scoring algorithms, quarantine evaluation, and slot reordering engine."""

from typing import List
from backend.config.models import ChannelSlot


class HealthRankingEngine:
    """Computes stream health scores (0-100), evaluates quarantine conditions, and sorts channel slots."""

    @staticmethod
    def calculate_health_score(
        status: str,
        uptime_pct: float = 100.0,
        latency_ms: float = 0.0,
        consecutive_errors: int = 0,
    ) -> float:
        """Calculates dynamic health score between 0.0 and 100.0 based on availability metrics.

        Formula:
            Score = (Status_OK * 40) + (Uptime_Ratio * 40) - min(20, Latency / 50) - (Consecutive_Errors * 15)

        Args:
            status (str): Stream link status ('online', 'offline', 'unchecked', etc.).
            uptime_pct (float): Uptime percentage (0.0 to 100.0).
            latency_ms (float): Response latency in milliseconds.
            consecutive_errors (int): Number of consecutive playback/probe errors.

        Returns:
            float: Normalized score between 0.0 and 100.0 rounded to 1 decimal place.
        """
        is_ok = 1.0 if str(status).lower() in ("online", "ok") else 0.0
        status_points = is_ok * 40.0

        clamped_uptime = max(0.0, min(100.0, float(uptime_pct)))
        uptime_points = (clamped_uptime / 100.0) * 40.0

        valid_latency = max(0.0, float(latency_ms))
        latency_penalty = min(20.0, valid_latency / 50.0)

        valid_errors = max(0, int(consecutive_errors))
        error_penalty = valid_errors * 15.0

        raw_score = status_points + uptime_points - latency_penalty - error_penalty
        return round(max(0.0, min(100.0, raw_score)), 1)

    @staticmethod
    def eval_quarantine_status(health_score: float, consecutive_errors: int = 0) -> bool:
        """Evaluates whether a stream must be placed into quarantine.

        A stream is quarantined when Health Score <= 20.0 or consecutive errors >= 3.

        Args:
            health_score (float): Computed stream health score.
            consecutive_errors (int): Consecutive error count.

        Returns:
            bool: True if stream must be quarantined, False otherwise.
        """
        return health_score <= 20.0 or consecutive_errors >= 3

    @staticmethod
    def reorder_slots(slots: List[ChannelSlot]) -> List[ChannelSlot]:
        """Reorders candidate stream slots by health score descending and assigns slot_index (0 to N-1).

        Locked slots (is_locked=True) remain prioritized at top.

        Args:
            slots (List[ChannelSlot]): List of stream slots (up to 7 items).

        Returns:
            List[ChannelSlot]: Reordered and re-indexed slots list.
        """
        if not slots:
            return []

        sorted_slots = sorted(
            slots,
            key=lambda s: (not s.is_locked, -s.health_score, s.consecutive_errors),
        )

        capped_slots = sorted_slots[:7]

        for idx, slot in enumerate(capped_slots):
            slot.slot_index = idx

        return capped_slots
