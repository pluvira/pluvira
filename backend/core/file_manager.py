"""Atomic file I/O operations and permission enforcement module."""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from backend.config.models import FilePermissions

if TYPE_CHECKING:
    from backend.core.notifier import Notifier


class FileManager:
    """Handles atomic file operations and Unix permissions for SMR/ZFS protection."""

    @staticmethod
    def atomic_write(
        src: Path,
        dest: Path,
        permissions: Optional[FilePermissions] = None,
        notifier: Optional["Notifier"] = None,
    ) -> None:
        """Atomically moves a file from RAM disk to final destination.

        Args:
            src (Path): Temporary source path.
            dest (Path): Target destination path.
            permissions (Optional[FilePermissions]): Unix permissions to apply.
            notifier (Optional["Notifier"]): Optional Notifier instance.
        """
        os.makedirs(dest.parent, exist_ok=True)
        temp_dest = dest.parent / f".temp_{dest.name}.{os.getpid()}"

        try:
            shutil.copy2(src, temp_dest)
            if permissions:
                FileManager._apply_permissions(temp_dest, permissions)
            os.replace(temp_dest, dest)
        except Exception as e:
            logging.error(f"Atomic write failed for '{dest}': {e}")
            try:
                from backend.core.notifier import Notifier
                notif = notifier or Notifier.from_config()
                notif.dispatch_event(
                    event_name="atomic_write_failure",
                    title="🔴 Pluvira: Atomic Write Failed",
                    body=f"Failed to persist file atomically from '{src}' to '{dest}'.\nError: {e}",
                    severity="critical",
                )
            except Exception:
                pass
            if temp_dest.exists():
                temp_dest.unlink()
            raise
        finally:
            if src.exists():
                src.unlink()

    @staticmethod
    def check_ram_disk_space(temp_dir: Path, min_free_mb: float = 30.0) -> bool:
        """Checks free disk space on RAM disk path.

        Args:
            temp_dir (Path): RAM disk directory path.
            min_free_mb (float): Minimum required free space in MB.

        Returns:
            bool: True if sufficient space, False otherwise.
        """
        try:
            usage = shutil.disk_usage(temp_dir)
            free_mb = usage.free / (1024 * 1024)
            return free_mb >= min_free_mb
        except Exception as e:
            logging.error(f"Failed to check RAM disk space for '{temp_dir}': {e}")
            return True


    @staticmethod
    def _apply_permissions(path: Path, perms: FilePermissions) -> None:
        """Applies Unix owner, group, and mode permissions.

        Args:
            path (Path): Target file path.
            perms (FilePermissions): Permission settings.
        """
        try:
            import pwd
            import grp
            uid = pwd.getpwnam(perms.owner).pw_uid
            gid = grp.getgrnam(perms.group).gr_gid
            os.chown(path, uid, gid)
            os.chmod(path, int(perms.mode, 8))
        except Exception as e:
            logging.warning(f"Could not apply permissions to '{path}': {e}")
