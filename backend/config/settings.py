"""Application settings loaded from environment variables and .env file."""

import os
import secrets
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-wide settings managed via environment variables."""

    config_dir: Path = Path("./config")
    data_dir: Path = Path("./data")
    temp_dir: Path = Path("/dev/shm/pluvira")
    pro_binary_path: Path = Path("./bin/pluvira-pro")

    config_file_name: str = "config.yaml"
    schedule_file_name: str = "schedule.yaml"

    api_host: str = "0.0.0.0"
    api_port: int = 8585

    storage_secret: str = ""

    cloud_base_url: str = "https://pluvira.com"

    @field_validator("config_dir", "data_dir", "temp_dir", "pro_binary_path", mode="after")
    @classmethod
    def resolve_absolute_paths(cls, value: Path) -> Path:
        """Resolves relative paths to absolute paths.

        Args:
            value (Path): Input directory path.

        Returns:
            Path: Resolved absolute path.
        """
        return value.resolve()

    @model_validator(mode="after")
    def resolve_storage_secret(self) -> "AppSettings":
        """Resolves storage_secret prioritizing ENV, persistent file, or generates new."""
        # 1. Check if explicitly set via ENV or constructor and meets minimum length
        if self.storage_secret and len(self.storage_secret.strip()) >= 32:
            return self

        env_secret = os.getenv("PLUVIRA_STORAGE_SECRET")
        if env_secret and env_secret.strip():
            self.storage_secret = env_secret.strip()
            return self

        # 2. Check disk file in data_dir / ".storage_secret"
        secret_file = self.data_dir / ".storage_secret"
        if secret_file.exists() and secret_file.is_file():
            try:
                content = secret_file.read_text(encoding="utf-8").strip()
                if content:
                    self.storage_secret = content
                    return self
            except Exception:
                pass

        # 3. Generate new 32-byte urlsafe secret and persist with 0600 permissions
        generated = secrets.token_urlsafe(32)
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(str(secret_file), flags, 0o600)
            with open(fd, "w", encoding="utf-8") as f:
                f.write(generated)
        except Exception:
            pass

        self.storage_secret = generated
        return self

    @property
    def config_path(self) -> Path:
        """Returns the absolute path to the main configuration file.

        Returns:
            Path: Absolute config file path.
        """
        return self.config_dir / self.config_file_name

    @property
    def cloud_endpoints(self) -> dict[str, str]:
        """Returns dictionary of SaaS cloud endpoint URLs."""
        base = self.cloud_base_url.rstrip("/")
        return {
            "base": base,
            "portal": f"{base}/portal",
            "auth": f"{base}/auth",
            "docs": f"{base}/docs",
        }

    @property
    def schedule_path(self) -> Path:
        """Returns the absolute path to the scheduler configuration file.

        Returns:
            Path: Absolute schedule file path.
        """
        return self.config_dir / self.schedule_file_name

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PLUVIRA_",
        extra="ignore",
    )


settings = AppSettings()
