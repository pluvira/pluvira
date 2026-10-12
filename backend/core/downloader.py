"""HTTP and local file acquisition module with gzip decompression."""

import os
import logging
import httpx
import shutil
import gzip
from pathlib import Path
from urllib.parse import urlparse, unquote


class Downloader:
    """Handles file acquisition from HTTP or local filesystem with Gzip support."""

    @staticmethod
    def download(url: str, dest: Path, user_agent: str) -> bool:
        """Acquires a remote HTTP URL or local file path safely into dest.

        Args:
            url (str): Target HTTP URL or file:// URI.
            dest (Path): Destination output path.
            user_agent (str): User-Agent header for HTTP requests.

        Returns:
            bool: True if successful, False if download failed.
        """
        logging.info(f"Acquiring file: {url}")
        os.makedirs(dest.parent, exist_ok=True)
        try:
            if url.startswith("file://"):
                parsed_path = unquote(urlparse(url).path)
                if os.name == "nt" and parsed_path.startswith("/") and len(parsed_path) > 2 and parsed_path[2] == ":":
                    parsed_path = parsed_path[1:]
                local_path = Path(parsed_path)
                if not local_path.exists():
                    logging.error(f"Local file not found: {local_path}")
                    return False
                shutil.copy2(local_path, dest)
                return True
            else:
                headers = {"User-Agent": user_agent}
                tmp_dest = dest.parent / f".download_{dest.name}.tmp.{os.getpid()}"
                try:
                    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
                        with client.stream("GET", url) as response:
                            response.raise_for_status()
                            with open(tmp_dest, "wb") as f:
                                for chunk in response.iter_bytes():
                                    f.write(chunk)
                    os.replace(tmp_dest, dest)
                    return True
                finally:
                    if tmp_dest.exists():
                        try:
                            tmp_dest.unlink()
                        except OSError:
                            pass
        except Exception as e:
            logging.error(f"Failed to acquire '{url}': {e}")
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
            return False

    @staticmethod
    def decompress_gzip(src: Path, dest: Path) -> bool:
        """Decompresses a .gz file to a destination path.

        Args:
            src (Path): Compressed input .gz path.
            dest (Path): Decompressed output path.

        Returns:
            bool: True if decompressed successfully, False on error.
        """
        try:
            os.makedirs(dest.parent, exist_ok=True)
            with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            return True
        except Exception as e:
            logging.error(f"Gzip decompression failed for '{src}': {e}")
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
            return False
