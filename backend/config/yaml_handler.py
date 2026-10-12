"""YAML configuration file loader and persistence handler."""

import os
import uuid
import logging
import threading
from pathlib import Path
from typing import Any, Optional, Callable
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from backend.config.settings import settings
from backend.config.models import GlobalConfig
from backend.core.file_manager import FileManager


class YAMLConfigHandler:
    """Handles thread-safe reading and atomic saving of config.yaml."""

    _lock = threading.RLock()

    def __init__(self, file_path: Optional[Path] = None) -> None:
        """Initializes handler with target YAML file path.

        Args:
            file_path (Optional[Path]): Override path to config.yaml.
        """
        self.file_path = file_path or settings.config_path
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def load_config(self) -> GlobalConfig:
        """Loads and validates config.yaml into GlobalConfig model.

        Returns:
            GlobalConfig: Validated global config object.

        Raises:
            ValueError: If YAML file is empty or corrupted.
        """
        with self._lock:
            if not self.file_path.exists():
                self._create_default_config()

            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = self.yaml.load(f)
                if raw_data is None:
                    raise ValueError("Configuration file is empty")
                return GlobalConfig.model_validate(raw_data)

    def save_config(self, config: GlobalConfig) -> None:
        """Atomically saves GlobalConfig model back to config.yaml preserving comments.

        Args:
            config (GlobalConfig): Validated config to persist.
        """
        with self._lock:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    commented_data = self.yaml.load(f) or CommentedMap()
            else:
                commented_data = CommentedMap()

            new_data = config.model_dump(exclude_none=True)
            updated_data = self._deep_update(commented_data, new_data)

            temp_file = self.file_path.with_suffix(f".tmp.{uuid.uuid4().hex}")
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    self.yaml.dump(updated_data, f)
                FileManager.atomic_write(temp_file, self.file_path)
            except Exception as e:
                logging.error(f"Failed to save config.yaml: {e}")
                try:
                    from backend.core.notifier import Notifier
                    notifier = Notifier.from_config(config)
                    notifier.dispatch_event(
                        event_name="config_save_failure",
                        title="🔴 Pluvira: Configuration Save Failed",
                        body=f"Failed to save configuration file '{self.file_path}'.\nError: {e}",
                        severity="critical",
                    )
                except Exception:
                    pass

                if temp_file.exists():
                    temp_file.unlink()
                raise

    def update_config(self, mutator_fn: Callable[[GlobalConfig], None]) -> GlobalConfig:
        """Atomically loads, mutates via callback, and saves configuration.

        Args:
            mutator_fn (Callable[[GlobalConfig], None]): Callback mutating the config object in-place.

        Returns:
            GlobalConfig: The updated and saved GlobalConfig instance.
        """
        with self._lock:
            config = self.load_config()
            mutator_fn(config)
            self.save_config(config)
            return config

    def _deep_update(self, target: Any, source: Any) -> Any:
        """Recursively updates ruamel.yaml CommentedMap structure preserving comments.

        Args:
            target (Any): Target CommentedMap/Seq structure.
            source (Any): Source dict/list.

        Returns:
            Any: Updated CommentedMap/Seq structure.
        """
        if isinstance(target, CommentedMap) and isinstance(source, dict):
            for k in [k for k in target.keys() if k not in source]:
                del target[k]
            for k, v in source.items():
                target[k] = self._deep_update(target[k], v) if k in target else self._to_commented(v)
            return target
        elif isinstance(target, CommentedSeq) and isinstance(source, list):
            while len(target) > len(source):
                target.pop()
            for i, item in enumerate(source):
                if i < len(target):
                    target[i] = self._deep_update(target[i], item)
                else:
                    target.append(self._to_commented(item))
            return target
        return source

    def _to_commented(self, data: Any) -> Any:
        """Converts dicts/lists to CommentedMap/CommentedSeq structures.

        Args:
            data (Any): Input python data structure.

        Returns:
            Any: Converted Commented structure.
        """
        if isinstance(data, dict):
            return CommentedMap({k: self._to_commented(v) for k, v in data.items()})
        elif isinstance(data, list):
            return CommentedSeq([self._to_commented(i) for i in data])
        return data

    def _create_default_config(self) -> None:
        """Creates a default config.yaml file if missing."""
        from backend.config.defaults import get_default_config_yaml

        os.makedirs(self.file_path.parent, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            self.yaml.dump(get_default_config_yaml(), f)
