"""Thread-safe state tracker for real-time acquisition update progress DTO."""

import time
import threading
from typing import List, Dict, Tuple, Optional

from backend.config.models import (
    UpdateSourceProgress,
    UpdatePhaseProgress,
    UpdateProgressSummary,
    UpdateProgressDTO,
)


class UpdateProgressTracker:
    """Manages thread-safe in-memory state transitions for background update runs."""

    def __init__(self) -> None:
        """Initializes empty state tracker with mutex lock."""
        self._lock = threading.Lock()
        self._is_running: bool = False
        self._mode: str = "idle"
        self._start_time: float = 0.0
        self._sources: List[UpdateSourceProgress] = []
        self._phases: Dict[str, UpdatePhaseProgress] = {}
        self._summary: Optional[UpdateProgressSummary] = None

    def reset(
        self,
        mode: str,
        m3u_sources: List[Tuple[str, bool]],
        epg_sources: List[Tuple[str, bool]],
    ) -> None:
        """Initializes tracker for a new acquisition run.

        Args:
            mode (str): Execution mode ('full', 'raw', 'm3u', 'epg').
            m3u_sources (List[Tuple[str, bool]]): List of (source_name, enabled) tuples.
            epg_sources (List[Tuple[str, bool]]): List of (epg_name, enabled) tuples.
        """
        with self._lock:
            self._is_running = True
            self._mode = mode
            self._start_time = time.time()
            self._summary = None
            self._sources = []

            for name, enabled in m3u_sources:
                if not enabled:
                    status, reason = "skipped", "disabled"
                elif mode not in ("full", "raw", "m3u"):
                    status, reason = "skipped", "not_in_mode"
                else:
                    status, reason = "pending", None
                self._sources.append(
                    UpdateSourceProgress(
                        name=name,
                        type="m3u",
                        status=status,
                        reason=reason,
                    )
                )

            for name, enabled in epg_sources:
                if not enabled:
                    status, reason = "skipped", "disabled"
                elif mode not in ("full", "raw", "epg"):
                    status, reason = "skipped", "not_in_mode"
                else:
                    status, reason = "pending", None
                self._sources.append(
                    UpdateSourceProgress(
                        name=name,
                        type="epg",
                        status=status,
                        reason=reason,
                    )
                )

            self._phases = {
                "rewrites": UpdatePhaseProgress(
                    title="Metadata Cascading Rewrites",
                    status="pending",
                    detail="Pending",
                ),
                "database_cache": UpdatePhaseProgress(
                    title="Saving Data & Cache Update",
                    status="pending",
                    detail="Pending",
                ),
            }

    def start_source(self, name: str) -> None:
        """Marks a source download as currently running.

        Args:
            name (str): Target source name.
        """
        with self._lock:
            for item in self._sources:
                if item.name == name and item.status != "skipped":
                    item.status = "running"
                    break

    def complete_source(
        self,
        name: str,
        channels: int = 0,
        programmes: int = 0,
        duration_s: float = 0.0,
        engine: str = "core",
        error: Optional[str] = None,
    ) -> None:
        """Records download result for a specific source.

        Args:
            name (str): Target source name.
            channels (int): Extracted channels count.
            programmes (int): Extracted EPG programmes count.
            error (Optional[str]): Error message if failed.
        """
        with self._lock:
            for item in self._sources:
                if item.name == name and item.status != "skipped":
                    if error:
                        item.status = "failed"
                        item.error = error
                    else:
                        item.status = "success"
                        item.channels = channels
                        item.programmes = programmes
                        item.duration_s = duration_s
                        item.engine = engine
                    break

    def update_phase(
        self, phase_id: str, status: str, detail: Optional[str] = None
    ) -> None:
        """Updates pipeline phase execution progress.

        Args:
            phase_id (str): Phase key ('rewrites' or 'database_cache').
            status (str): Target status ('pending', 'running', 'success', 'failed').
            detail (Optional[str]): Informational progress detail.
        """
        with self._lock:
            if phase_id in self._phases:
                self._phases[phase_id].status = status
                if detail:
                    self._phases[phase_id].detail = detail

    def finish(
        self,
        status: str,
        duration: float,
        total_channels: int = 0,
        matched_channels: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Finalizes update run and commits summary.

        Args:
            status (str): Overall run status ('success' or 'failed').
            duration (float): Total execution duration in seconds.
            total_channels (int): Total channels processed.
            matched_channels (int): Channels mapped to EPG.
            error (Optional[str]): Fatal error message if failed.
        """
        with self._lock:
            self._is_running = False
            for p in self._phases.values():
                if status == "success" and p.status in ("pending", "running"):
                    p.status = "success"
                elif status == "failed" and p.status == "running":
                    p.status = "failed"

            self._summary = UpdateProgressSummary(
                status=status,
                duration=round(duration, 2),
                total_channels=total_channels,
                matched_channels=matched_channels,
                error_message=error,
            )

    def get_snapshot(self) -> UpdateProgressDTO:
        """Retrieves an immutable point-in-time DTO snapshot.

        Returns:
            UpdateProgressDTO: Current state model.
        """
        with self._lock:
            elapsed = 0.0
            if self._is_running and self._start_time > 0:
                elapsed = round(time.time() - self._start_time, 1)

            return UpdateProgressDTO(
                is_running=self._is_running,
                mode=self._mode,
                elapsed_seconds=elapsed,
                sources=[item.model_copy() for item in self._sources],
                phases={k: v.model_copy() for k, v in self._phases.items()},
                summary=self._summary.model_copy() if self._summary else None,
            )


update_progress_tracker = UpdateProgressTracker()
