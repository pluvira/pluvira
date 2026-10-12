"""System health monitoring service for CPU load and thermal readings."""

import os
import uuid
import logging
import hashlib
import multiprocessing
from pathlib import Path
from typing import Optional, List
from backend.config.settings import settings
from backend.config.models import GlobalConfig
from backend.core.file_manager import FileManager
from backend.core.identity import get_device_hash as identity_get_device_hash


def get_device_hash() -> str:
    """Resolves or generates a stable SHA-256 device fingerprint."""
    return identity_get_device_hash()


class SystemHealth:
    """Utility service to monitor CPU load and system temperature on Linux/Unix."""

    @staticmethod
    def get_device_hash() -> str:
        """Returns stable device hash."""
        return get_device_hash()

    @staticmethod
    def get_cpu_load() -> float:
        """Returns 1-minute CPU load average normalized as percentage of total cores.

        Returns:
            float: Normalized CPU load percentage (0.0 to 100.0+).
        """
        try:
            load1, _, _ = os.getloadavg()
            cpus = multiprocessing.cpu_count()
            return round((load1 / cpus) * 100.0, 1)
        except (AttributeError, OSError):
            return 0.0

    @staticmethod
    def get_temperature() -> Optional[float]:
        """Reads system thermal zone temperature in Celsius on Linux.

        Returns:
            Optional[float]: Temperature in °C or None if unreadable.
        """
        thermal_paths = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp",
        ]
        for path in thermal_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return round(float(f.read().strip()) / 1000.0, 1)
                except (ValueError, OSError):
                    continue
        return None

    @staticmethod
    def check_system_health(config: GlobalConfig) -> List[str]:
        """Checks CPU load and temperature against thresholds and dispatches warnings.

        Args:
            config (GlobalConfig): GlobalConfig instance.

        Returns:
            List[str]: List of warnings if thresholds exceeded.
        """
        events = config.get_event_config()

        reasons = []
        cpu_load = SystemHealth.get_cpu_load()
        cpu_threshold = events.cpu_load_threshold_pct
        if cpu_load > cpu_threshold:
            reasons.append(f"CPU Load: {cpu_load}% (Threshold: {cpu_threshold}%)")

        temp = SystemHealth.get_temperature()
        temp_threshold = events.temp_threshold_c
        if temp is not None and temp > temp_threshold:
            reasons.append(f"Temperature: {temp:.1f}°C (Threshold: {temp_threshold}°C)")

        if reasons:
            try:
                from backend.core.notifier import Notifier
                notifier = Notifier.from_config(config)
                notifier.dispatch_event(
                    event_name="system_high_load",
                    title="⚠️ Pluvira: System High Load",
                    body="System hardware thresholds exceeded:\n- " + "\n- ".join(reasons),
                    severity="warning",
                )
            except Exception as e:
                logging.error(f"Failed to dispatch system_high_load notification: {e}")

        return reasons
