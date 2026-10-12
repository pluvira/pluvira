"""Appliance instance identity engine."""

import os
import re
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Optional

from backend.config.settings import settings

INSTANCE_ID_REGEX = re.compile(r"^[a-f0-9]{64}$")
DEFAULT_SALT_FALLBACK = "pluvira_instance_identity_salt"


def get_or_create_instance_id(data_dir: Optional[Path] = None) -> str:
    """Retrieves or atomically creates the persistent appliance instance identifier.

    Binds identity strictly to data/.instance_id in persistent storage.
    Generates a 32-byte CSPRNG token (64 hex characters) with POSIX 0600 permissions.

    Args:
        data_dir (Optional[Path]): Override directory for storage location.

    Returns:
        str: 64-character lowercase hexadecimal instance identifier.
    """
    target_dir = data_dir or settings.data_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    instance_file = target_dir / ".instance_id"

    if instance_file.exists() and instance_file.is_file():
        try:
            content = instance_file.read_text(encoding="utf-8").strip()
            if INSTANCE_ID_REGEX.match(content):
                return content
        except Exception:
            pass

    # Generate new 32-byte CSPRNG token (64 hex characters)
    new_instance_id = secrets.token_hex(32).lower()
    temp_file = instance_file.with_suffix(f".tmp.{os.getpid()}")

    try:
        temp_file.write_text(new_instance_id + "\n", encoding="utf-8")
        try:
            os.chmod(temp_file, 0o600)
        except OSError:
            pass
        os.replace(temp_file, instance_file)
        try:
            os.chmod(instance_file, 0o600)
        except OSError:
            pass
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass

    return new_instance_id


def get_device_hash(data_dir: Optional[Path] = None, salt: Optional[str] = None) -> str:
    """Computes deterministic device hash from persistent instance identity.

    Formula:
        device_hash = HMAC-SHA256(key=LOCAL_SALT, data=instance_id)

    Args:
        data_dir (Optional[Path]): Override directory for storage location.
        salt (Optional[str]): Salt key for HMAC derivation.

    Returns:
        str: 64-character lowercase hexadecimal HMAC-SHA256 digest.
    """
    instance_id = get_or_create_instance_id(data_dir)
    effective_salt = salt or settings.storage_secret or DEFAULT_SALT_FALLBACK
    return hmac.new(
        key=effective_salt.encode("utf-8"),
        msg=instance_id.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def reset_instance_identity(data_dir: Optional[Path] = None) -> None:
    """Permanently deletes the persistent instance identifier file.

    Args:
        data_dir (Optional[Path]): Override directory for storage location.
    """
    target_dir = data_dir or settings.data_dir
    instance_file = target_dir / ".instance_id"
    if instance_file.exists():
        try:
            instance_file.unlink()
        except OSError:
            pass
