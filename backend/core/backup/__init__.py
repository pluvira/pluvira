"""Configuration backup, migration, and serialization package."""

from backend.core.backup.sanitizer import BackupSanitizer
from backend.core.backup.migrator import MigrationManager, CURRENT_SCHEMA_VERSION
from backend.core.backup.validator import BackupValidator
from backend.core.backup.crypto import encrypt_packet, decrypt_packet
from backend.core.backup.bundle import (
    BackupBundle,
    BackupScheduleData,
    BackupDiffSummary,
    DiffCategoryCount,
    BackupValidationResult,
    BackupImportPayload,
    BackupImportResult,
)

__all__ = [
    "BackupSanitizer",
    "MigrationManager",
    "CURRENT_SCHEMA_VERSION",
    "BackupValidator",
    "BackupBundle",
    "BackupScheduleData",
    "BackupDiffSummary",
    "DiffCategoryCount",
    "BackupValidationResult",
    "BackupImportPayload",
    "BackupImportResult",
    "encrypt_packet",
    "decrypt_packet",
]
