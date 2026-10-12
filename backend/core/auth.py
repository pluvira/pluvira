"""JWT Authentication core service for headless API security."""

import time
import hmac
import json
import base64
import hashlib
import logging
from typing import Optional, Dict, Any



def _base64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    """Decodes base64url string with missing padding."""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta_minutes: int = 1440,
) -> str:
    """Creates a signed JWT HS256 access token.

    Args:
        data (Dict[str, Any]): Claims payload (must include 'sub').
        secret_key (str): Secret key for signing.
        algorithm (str): HMAC algorithm (default HS256).
        expires_delta_minutes (int): Expiration time in minutes.

    Returns:
        str: Signed JWT string.
    """
    header = {"alg": algorithm, "typ": "JWT"}
    now = int(time.time())
    payload = {
        **data,
        "iat": now,
        "exp": now + (expires_delta_minutes * 60),
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT HS256 access token.

    Args:
        token (str): Raw JWT token.
        secret_key (str): Secret key for signature verification.
        algorithm (str): Expected algorithm.

    Returns:
        Optional[Dict[str, Any]]: Valid payload dictionary or None if invalid/expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if exp and int(time.time()) > exp:
            return None

        return payload
    except Exception as e:
        logging.error(f"Failed to decode JWT token: {e}")
        return None




