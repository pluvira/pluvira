"""Runtime version and environment resolution engine."""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from backend.config.settings import settings

SAFETY_FALLBACK_VERSION: str = "0.0.0.dev0"

_version_cache: Optional[Tuple[str, Optional[str]]] = None


def clear_version_cache() -> None:
    """Clears cached version and git hash info."""
    global _version_cache
    _version_cache = None


def _resolve_git(repo_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """Resolves Git tag, commit hash, and dirty status.

    Args:
        repo_dir (Path): Repository root path.

    Returns:
        Tuple[Optional[str], Optional[str]]: (version, git_hash).
    """
    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        return None, None

    git_hash: Optional[str] = None
    try:
        p_hash = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if p_hash.returncode == 0 and p_hash.stdout.strip():
            git_hash = p_hash.stdout.strip()

        is_dirty = False
        p_stat = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if p_stat.returncode == 0 and p_stat.stdout.strip():
            is_dirty = True

        p_exact = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if p_exact.returncode == 0 and p_exact.stdout.strip():
            exact_tag = p_exact.stdout.strip()
            return (f"{exact_tag}.dirty" if is_dirty else exact_tag), git_hash

        p_latest = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        latest_tag = p_latest.stdout.strip() if p_latest.returncode == 0 and p_latest.stdout.strip() else None
        if latest_tag and git_hash:
            base = f"{latest_tag}+{git_hash}"
            return (f"{base}.dirty" if is_dirty else base), git_hash
        elif git_hash:
            base = f"{SAFETY_FALLBACK_VERSION}+{git_hash}"
            return (f"{base}.dirty" if is_dirty else base), git_hash
    except Exception:
        pass

    return None, git_hash


def get_version_info() -> Tuple[str, Optional[str]]:
    """Resolves release version and git hash following priority hierarchy.

    Returns:
        Tuple[str, Optional[str]]: Tuple of (version, git_hash).
    """
    global _version_cache
    if _version_cache is not None:
        return _version_cache

    version: Optional[str] = None
    git_hash: Optional[str] = None

    try:
        import _version  # type: ignore

        version = getattr(_version, "__version__", getattr(_version, "version", None))
    except ImportError:
        pass

    env_ver = os.getenv("PLUVIRA_VERSION")
    if not version and env_ver and env_ver.strip():
        version = env_ver.strip()

    env_h = os.getenv("PLUVIRA_GIT_HASH")
    if env_h and env_h.strip():
        git_hash = env_h.strip()

    if not version or not git_hash:
        g_ver, g_hash = _resolve_git(Path(__file__).resolve().parent.parent.parent)
        if not version and g_ver:
            version = g_ver
        if not git_hash and g_hash:
            git_hash = g_hash

    if not version:
        version_file = Path("VERSION")
        if version_file.exists():
            try:
                content = version_file.read_text(encoding="utf-8").strip()
                if content:
                    version = content
            except Exception:
                pass

    if not version:
        try:
            import importlib.metadata
            version = importlib.metadata.version("pluvira")
        except Exception:
            pass

    resolved_version = version or SAFETY_FALLBACK_VERSION
    _version_cache = (resolved_version, git_hash)
    return _version_cache


def get_environment_info() -> Dict[str, Any]:
    """Resolves environment paths and runtime version metadata.

    Returns:
        Dict[str, Any]: Environment diagnostics dictionary.
    """
    ver, g_hash = get_version_info()
    return {
        "version": ver,
        "git_hash": g_hash,
        "config_path": str(settings.config_path),
        "data_dir": str(settings.data_dir),
        "temp_dir": str(settings.temp_dir),
    }


def get_version() -> str:
    """Returns resolved release version string.

    Returns:
        str: Resolved version.
    """
    ver, _ = get_version_info()
    return ver
