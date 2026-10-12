"""Inter-process lock manager operating on RAM disk."""

import os
import time
import logging
from pathlib import Path
from typing import Optional

from backend.config.settings import settings


class LockManager:
    """Manages system execution lock file in RAM disk to prevent process collisions."""

    def __init__(self, temp_dir: Optional[Path] = None) -> None:
        """Initializes lock manager with target lock file path.

        Args:
            temp_dir (Optional[Path]): Override RAM disk temp directory.
        """
        self.temp_dir = temp_dir or settings.temp_dir
        self.lock_file = self.temp_dir / "pluvira_update.lock"

    def acquire(self) -> bool:
        """Attempts to acquire lock file. Auto-clears orphaned locks older than 30 mins.

        Returns:
            bool: True if lock acquired, False if already locked.
        """
        if self.lock_file.exists():
            try:
                mtime = self.lock_file.stat().st_mtime
                pid = self._read_lock_pid()
                is_stale = (pid is not None and not self._is_pid_running(pid))
                if is_stale or (time.time() - mtime > 1800):
                    logging.warning(f"Orphaned stale lock file detected on {self.lock_file}. Recovering...")
                    self._notify_orphan_lock(mtime)
                    self.release()
                else:
                    return False
            except Exception as e:
                logging.error(f"Error inspecting lock file '{self.lock_file}': {e}")
                return False

        try:
            os.makedirs(self.lock_file.parent, exist_ok=True)
            self.lock_file.write_text(str(os.getpid()), encoding="utf-8")
            return True
        except Exception as e:
            logging.error(f"Failed to create lock file '{self.lock_file}': {e}")
            return False

    def release(self) -> None:
        """Releases and removes the lock file if present."""
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except Exception as e:
                logging.error(f"Failed to remove lock file '{self.lock_file}': {e}")

    def is_locked(self) -> bool:
        """Checks if process lock file currently exists.

        Returns:
            bool: True if locked, False otherwise.
        """
        return self.lock_file.exists()

    def _read_lock_pid(self) -> Optional[int]:
        """Reads process ID stored in the lock file if valid."""
        try:
            content = self.lock_file.read_text(encoding="utf-8").strip()
            return int(content) if content.isdigit() else None
        except Exception:
            return None

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Checks if a process with given PID is currently active."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True
        except OSError:
            return False

    def _notify_orphan_lock(self, mtime: float) -> None:
        """Dispatches orphan lock recovery notification event.

        Args:
            mtime (float): Lock file modification timestamp.
        """
        try:
            from backend.core.notifier import Notifier
            notifier = Notifier.from_config()
            age_mins = int((time.time() - mtime) // 60)
            notifier.dispatch_event(
                event_name="orphan_lock_recovered",
                title="⚠️ Pluvira: Orphan Lock Cleared",
                body=f"An orphaned stale lock file was detected and auto-cleared.\nLock File: {self.lock_file}\nAge: {age_mins} minutes.",
                severity="warning",
            )
        except Exception as e:
            logging.error(f"Failed to dispatch orphan lock notification: {e}")
