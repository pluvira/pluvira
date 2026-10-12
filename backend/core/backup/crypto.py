"""Cryptographic utilities for Zero-Knowledge E2EE backup packets (PBKDF2 + AES-256-GCM with authenticated fallback)."""

import os
import gzip
import hmac
import base64
import hashlib
from typing import Tuple

from backend.core.exceptions import ValidationDomainError

# Dual-Engine Cryptographic Architecture:
# 1. Primary Engine: Hardware-accelerated native AES-256-GCM via 'cryptography' library
# 2. Portability Fallback: Pure-Python PBKDF2-HMAC-SHA256 + SHA256-CTR + HMAC-SHA256 Encrypt-then-MAC
#    (Designed for low-power NAS and constrained edge environments lacking precompiled C wheels)
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover
    AESGCM = None

PBKDF2_ITERATIONS = 600_000


def encrypt_packet(data_bytes: bytes, passphrase: str) -> Tuple[str, str]:
    """Encrypts data bytes with PBKDF2 (600,000 iterations) + AES-256-GCM.

    Args:
        data_bytes (bytes): Plaintext unencrypted binary payload.
        passphrase (str): User private encryption passphrase.

    Returns:
        Tuple[str, str]: Base64 encoded ciphertext packet and SHA-256 checksum.
    """
    compressed = gzip.compress(data_bytes)
    salt = os.urandom(16)
    iv = os.urandom(12)

    if AESGCM is not None:
        # Primary Engine: Native Hardware-Accelerated AES-256-GCM
        key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(iv, compressed, None)
    else:
        # Fallback Engine: Authenticated PBKDF2-HMAC-SHA256 + SHA256-CTR + HMAC-SHA256
        derived = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=64)
        enc_key, mac_key = derived[:32], derived[32:]
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(compressed):
            block = hashlib.sha256(enc_key + iv + counter.to_bytes(4, "big")).digest()
            keystream.extend(block)
            counter += 1
        ct_bytes = bytes(b ^ k for b, k in zip(compressed, keystream[:len(compressed)]))
        tag = hmac.new(mac_key, salt + iv + ct_bytes, hashlib.sha256).digest()[:16]
        ciphertext = ct_bytes + tag

    packet = salt + iv + ciphertext
    sha256_checksum = hashlib.sha256(packet).hexdigest()
    encrypted_blob = base64.b64encode(packet).decode("utf-8")
    return encrypted_blob, sha256_checksum


def decrypt_packet(encrypted_blob: str, passphrase: str) -> bytes:
    """Decrypts Base64 encoded packet using PBKDF2 + AES-256-GCM and decompresses gzip payload.

    Args:
        encrypted_blob (str): Base64 encoded payload packet.
        passphrase (str): User private decryption passphrase.

    Returns:
        bytes: Decrypted and decompressed plaintext bytes.

    Raises:
        ValidationDomainError: If packet is invalid, tag mismatch, or corrupted.
    """
    try:
        packet = base64.b64decode(encrypted_blob)
    except Exception as e:
        raise ValidationDomainError(f"Invalid base64 payload: {e}")

    if len(packet) < 16 + 12 + 16:
        raise ValidationDomainError("Invalid or corrupted cloud backup payload: packet too short.")

    salt = packet[:16]
    iv = packet[16:28]
    ciphertext = packet[28:]

    try:
        if AESGCM is not None:
            # Primary Engine: Native Hardware-Accelerated AES-256-GCM
            key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32)
            aesgcm = AESGCM(key)
            compressed = aesgcm.decrypt(iv, ciphertext, None)
            return gzip.decompress(compressed)
        else:
            # Fallback Engine: Authenticated PBKDF2-HMAC-SHA256 + SHA256-CTR + HMAC-SHA256
            derived = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=64)
            enc_key, mac_key = derived[:32], derived[32:]
            if len(ciphertext) < 16:
                raise ValidationDomainError("Decryption failed: Ciphertext too short.")
            ct_bytes = ciphertext[:-16]
            expected_tag = ciphertext[-16:]
            actual_tag = hmac.new(mac_key, salt + iv + ct_bytes, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(expected_tag, actual_tag):
                raise ValidationDomainError("Decryption failed: Incorrect passphrase or corrupted backup snapshot.")
            keystream = bytearray()
            counter = 0
            while len(keystream) < len(ct_bytes):
                block = hashlib.sha256(enc_key + iv + counter.to_bytes(4, "big")).digest()
                keystream.extend(block)
                counter += 1
            compressed = bytes(b ^ k for b, k in zip(ct_bytes, keystream[:len(ct_bytes)]))
            return gzip.decompress(compressed)
    except ValidationDomainError:
        raise
    except Exception:
        raise ValidationDomainError("Decryption failed: Incorrect passphrase or corrupted backup snapshot.")
