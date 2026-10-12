"""RAM disk artwork caching engine for EPG posters and backdrops."""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

import httpx

from backend.config.settings import settings
from backend.core.file_manager import FileManager


class ArtworkCache:
    """Manages high-speed volatile caching of external artwork images in RAM disk."""

    def __init__(self, cache_dir: Optional[Path] = None, min_free_mb: float = 30.0) -> None:
        """Initializes artwork cache directory in RAM disk.

        Args:
            cache_dir (Optional[Path]): Override RAM disk directory path.
            min_free_mb (float): Minimum RAM disk free space threshold in MB.
        """
        self.cache_dir = cache_dir or (settings.temp_dir / "artwork_cache")
        self.min_free_mb = min_free_mb
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_image_hash(image_url: str) -> str:
        """Computes deterministic hash filename for image URL preserving extension.

        Args:
            image_url (str): Remote image URL.

        Returns:
            str: Normalized hash filename with extension.
        """
        ext = ".jpg"
        clean_url = image_url.split("?")[0].lower()
        for candidate_ext in (".png", ".webp", ".jpg", ".jpeg", ".svg"):
            if clean_url.endswith(candidate_ext):
                ext = candidate_ext
                break
        url_hash = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:32]
        return f"{url_hash}{ext}"

    def get_image_path(self, image_hash: str) -> Optional[Path]:
        """Returns physical file path if cached on RAM disk, else None.

        Args:
            image_hash (str): Filename or hash identifier.

        Returns:
            Optional[Path]: Existing file path or None.
        """
        safe_name = Path(image_hash).name
        target = self.cache_dir / safe_name
        if target.exists() and target.is_file():
            try:
                os.utime(target, None)
            except OSError:
                pass
            return target
        return None

    async def save_image(
        self,
        image_url: str,
        image_hash: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[str]:
        """Downloads and stores remote artwork to RAM disk with atomic write.

        Args:
            image_url (str): Remote image URL.
            image_hash (Optional[str]): Explicit filename or None to compute.
            client (Optional[httpx.AsyncClient]): Optional HTTP client.

        Returns:
            Optional[str]: Cached filename if successfully stored, None otherwise.
        """
        if not image_url or not image_url.startswith(("http://", "https://")):
            return None

        filename = image_hash or self.compute_image_hash(image_url)
        target_path = self.cache_dir / filename

        if target_path.exists() and target_path.is_file():
            return filename

        if not FileManager.check_ram_disk_space(self.cache_dir, min_free_mb=self.min_free_mb):
            pruned = self.prune_lru(max_files_to_delete=20)
            if pruned == 0 and not FileManager.check_ram_disk_space(self.cache_dir, min_free_mb=self.min_free_mb):
                logging.warning("RAM disk artwork cache full; skipping image caching.")
                return None

        try:
            if client:
                resp = await client.get(image_url, timeout=8.0)
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.get(image_url, timeout=8.0)

            if resp.status_code != 200 or not resp.content:
                return None

            temp_path = self.cache_dir / f".temp_{filename}.{os.getpid()}"
            temp_path.write_bytes(resp.content)
            os.replace(temp_path, target_path)
            return filename
        except Exception as e:
            logging.debug(f"Artwork cache download failed for '{image_url}': {e}")
            return None

    def prune_lru(self, max_files_to_delete: int = 50) -> int:
        """Prunes least recently used/accessed artwork files.

        Args:
            max_files_to_delete (int): Maximum batch size of files to remove.

        Returns:
            int: Number of files deleted.
        """
        if not self.cache_dir.exists():
            return 0

        files = []
        for p in self.cache_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                try:
                    files.append((p.stat().st_mtime, p))
                except OSError:
                    pass

        if not files:
            return 0

        files.sort(key=lambda x: x[0])
        deleted = 0
        for _, file_path in files[:max_files_to_delete]:
            try:
                file_path.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                pass
        return deleted

    def clear(self) -> None:
        """Removes all cached images from RAM disk."""
        if self.cache_dir.exists():
            for p in self.cache_dir.iterdir():
                if p.is_file():
                    try:
                        p.unlink(missing_ok=True)
                    except OSError:
                        pass

    def get_count(self) -> int:
        """Returns total count of cached artwork files.

        Returns:
            int: Number of files in cache directory.
        """
        if not self.cache_dir.exists():
            return 0
        return sum(1 for p in self.cache_dir.iterdir() if p.is_file() and not p.name.startswith("."))
