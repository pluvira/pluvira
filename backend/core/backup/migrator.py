"""Schema migration registry and version upgrade engine for configuration files and backup bundles."""

from pathlib import Path
from typing import Dict, Any, Callable, Tuple, Optional

from backend.core.exceptions import InvalidConfigurationError

CURRENT_SCHEMA_VERSION: int = 1


class MigrationManager:
    """Manages schema version detection, migrations, and backward compatibility pipelines."""

    _config_migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
    _schedule_migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @classmethod
    def register_config_migration(
        cls, from_version: int, func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Registers a stepwise migration callback for config schemas.

        Args:
            from_version (int): Source version to migrate from.
            func (Callable[[Dict[str, Any]], Dict[str, Any]]): Transformation function.
        """
        cls._config_migrations[from_version] = func

    @classmethod
    def register_schedule_migration(
        cls, from_version: int, func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Registers a stepwise migration callback for scheduler schemas.

        Args:
            from_version (int): Source version to migrate from.
            func (Callable[[Dict[str, Any]], Dict[str, Any]]): Transformation function.
        """
        cls._schedule_migrations[from_version] = func

    @classmethod
    def migrate_config_dict(
        cls, raw_data: Dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION
    ) -> Tuple[Dict[str, Any], bool]:
        """Migrates a configuration dictionary to target schema version.

        Args:
            raw_data (Dict[str, Any]): Raw configuration dictionary.
            target_version (int): Target schema version to reach.

        Returns:
            Tuple[Dict[str, Any], bool]: Migrated dictionary and boolean indicating if migration occurred.

        Raises:
            InvalidConfigurationError: If schema version exceeds max supported target version.
        """
        current_v = int(raw_data.get("version", 1))

        if current_v > target_version:
            raise InvalidConfigurationError(
                f"Unsupported configuration schema version {current_v}. Max supported version is {target_version}."
            )

        if current_v == target_version:
            raw_data["version"] = target_version
            return raw_data, False

        migrated = dict(raw_data)
        v = current_v
        while v < target_version:
            if v in cls._config_migrations:
                migrated = cls._config_migrations[v](migrated)
            v += 1

        migrated["version"] = target_version
        return migrated, True

    @classmethod
    def migrate_schedule_dict(
        cls, raw_data: Dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION
    ) -> Tuple[Dict[str, Any], bool]:
        """Migrates a scheduler configuration dictionary to target schema version.

        Args:
            raw_data (Dict[str, Any]): Raw schedule dictionary.
            target_version (int): Target schema version to reach.

        Returns:
            Tuple[Dict[str, Any], bool]: Migrated dictionary and boolean indicating if migration occurred.

        Raises:
            InvalidConfigurationError: If schema version exceeds max supported target version.
        """
        current_v = int(raw_data.get("version", 1))

        if current_v > target_version:
            raise InvalidConfigurationError(
                f"Unsupported schedule schema version {current_v}. Max supported version is {target_version}."
            )

        if current_v == target_version:
            raw_data["version"] = target_version
            return raw_data, False

        migrated = dict(raw_data)
        v = current_v
        while v < target_version:
            if v in cls._schedule_migrations:
                migrated = cls._schedule_migrations[v](migrated)
            v += 1

        migrated["version"] = target_version
        return migrated, True

    @classmethod
    def migrate_bundle_dict(
        cls, bundle_dict: Dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION
    ) -> Tuple[Dict[str, Any], bool]:
        """Migrates an entire backup bundle dictionary to target schema version.

        Args:
            bundle_dict (Dict[str, Any]): Raw bundle dictionary.
            target_version (int): Target schema version.

        Returns:
            Tuple[Dict[str, Any], bool]: Migrated bundle dictionary and migration flag.
        """
        migrated = False

        if "config" in bundle_dict and isinstance(bundle_dict["config"], dict):
            migrated_cfg, cfg_changed = cls.migrate_config_dict(
                bundle_dict["config"], target_version=target_version
            )
            bundle_dict["config"] = migrated_cfg
            if cfg_changed:
                migrated = True

        if "schedule" in bundle_dict and isinstance(bundle_dict["schedule"], dict):
            migrated_sch, sch_changed = cls.migrate_schedule_dict(
                bundle_dict["schedule"], target_version=target_version
            )
            bundle_dict["schedule"] = migrated_sch
            if sch_changed:
                migrated = True

        bundle_dict["bundle_version"] = target_version
        return bundle_dict, migrated

    @classmethod
    def check_and_migrate_disk_configs(
        cls, config_path: Optional[Path] = None, schedule_path: Optional[Path] = None
    ) -> bool:
        """No-op: Disk config auto-migrations disabled."""

        return False


