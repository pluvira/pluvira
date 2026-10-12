"""mDNS (Zeroconf) network discovery service for Pluvira server identity."""

import re
import socket
import logging
import threading
from typing import Optional, Dict, Any, List

try:
    from zeroconf import Zeroconf, ServiceInfo
    ZEROCONF_AVAILABLE = True
except ImportError:  # pragma: no cover
    Zeroconf = None  # type: ignore[assignment, misc]
    ServiceInfo = None  # type: ignore[assignment, misc]
    ZEROCONF_AVAILABLE = False

from backend import __version__
from backend.config.settings import settings
from backend.config.models import MdnsConfig
from backend.core.system_health import SystemHealth
from backend.core.pro_bridge import ProBridge
from backend.core.db import DatabaseManager


def _get_local_ips() -> List[bytes]:
    """Resolves local host IP addresses formatted as raw bytes for Zeroconf.

    Returns:
        List[bytes]: List of packed IPv4 addresses in network byte order.
    """
    ips: List[bytes] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip_str = s.getsockname()[0]
        s.close()
        ips.append(socket.inet_aton(ip_str))
    except Exception:
        pass

    if not ips:
        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            ips.append(socket.inet_aton(host_ip))
        except Exception:
            ips.append(socket.inet_aton("127.0.0.1"))

    return ips


class MdnsService:
    """Service handling local mDNS (Zeroconf) service registration and discovery broadcasts."""

    def __init__(self) -> None:
        """Initializes unstarted mDNS discovery service."""
        self._zc: Optional[Any] = None
        self._service_info: Optional[Any] = None
        self._is_running: bool = False
        self._current_device_name: str = "Pluvira"
        self._current_config: Optional[MdnsConfig] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Returns whether mDNS service is currently advertising.

        Returns:
            bool: True if service is actively registered, False otherwise.
        """
        return self._is_running

    def get_txt_records(self, device_name: str) -> Dict[str, str]:
        """Composes standard TXT metadata records for mDNS broadcast.

        Args:
            device_name (str): Device instance broadcast name.

        Returns:
            Dict[str, str]: Metadata key-value mappings.
        """
        edition = "core"
        try:
            edition_info = ProBridge.get_edition_info()
            if isinstance(edition_info, dict):
                edition = edition_info.get("edition", "core")
        except Exception:
            pass

        uid = ""
        try:
            cloud_id = DatabaseManager.get_cloud_identity()
            if isinstance(cloud_id, dict):
                uid = cloud_id.get("uid") or ""
        except Exception:
            pass

        device_hash = ""
        try:
            device_hash = SystemHealth.get_device_hash()
        except Exception:
            pass

        return {
            "name": device_name,
            "version": __version__,
            "edition": edition,
            "port": str(settings.api_port),
            "uid": uid,
            "device_hash": device_hash[:16] if device_hash else "",
        }

    def start(
        self,
        device_name: Optional[str] = None,
        mdns_config: Optional[MdnsConfig] = None,
    ) -> bool:
        """Registers and starts advertising mDNS service on local network.

        Args:
            device_name (Optional[str]): Explicit device name override.
            mdns_config (Optional[MdnsConfig]): Explicit mDNS configuration override.

        Returns:
            bool: True if registration succeeded, False otherwise.
        """
        with self._lock:
            if self._is_running:
                logging.debug("mDNS discovery service already running.")
                return True

            if not ZEROCONF_AVAILABLE:
                logging.warning("zeroconf library is not available. mDNS discovery disabled.")
                return False

            if device_name is None or mdns_config is None:
                try:
                    from backend.config.yaml_handler import YAMLConfigHandler
                    cfg = YAMLConfigHandler().load_config()
                    if device_name is None:
                        device_name = cfg.settings.device_name or "Pluvira"
                    if mdns_config is None:
                        mdns_config = cfg.settings.mdns or MdnsConfig()
                except Exception as e:
                    logging.warning(f"Failed to load config for mDNS: {e}")
                    device_name = device_name or "Pluvira"
                    mdns_config = mdns_config or MdnsConfig()

            if not mdns_config.enabled:
                logging.info("mDNS discovery is disabled in configuration.")
                return False

            self._current_device_name = device_name
            self._current_config = mdns_config

            service_type = mdns_config.service_type
            if not service_type.endswith("."):
                service_type = f"{service_type}."

            service_name = f"{device_name}.{service_type}"
            slug = re.sub(r"[^a-zA-Z0-9-]", "-", device_name).strip("-").lower() or "pluvira"
            server_host = f"{slug}.local."
            addresses = _get_local_ips()
            port = settings.api_port
            txt_records = self.get_txt_records(device_name)
            properties = {k.encode("utf-8"): v.encode("utf-8") for k, v in txt_records.items()}

            try:
                self._service_info = ServiceInfo(
                    type_=service_type,
                    name=service_name,
                    addresses=addresses,
                    port=port,
                    properties=properties,
                    server=server_host,
                )
                self._zc = Zeroconf()
                self._zc.register_service(self._service_info)
                self._is_running = True
                logging.info(f"📡 mDNS service registered: {service_name} on port {port} ({server_host})")
                return True
            except Exception as e:
                logging.warning(f"Failed to register mDNS service: {e}")
                if self._zc:
                    try:
                        self._zc.close()
                    except Exception:
                        pass
                self._zc = None
                self._service_info = None
                self._is_running = False
                return False

    def stop(self) -> None:
        """Unregisters mDNS service and closes Zeroconf instance."""
        with self._lock:
            if not self._is_running and self._zc is None:
                return

            logging.info("Stopping mDNS service discovery...")
            if self._zc and self._service_info:
                try:
                    self._zc.unregister_service(self._service_info)
                except Exception as e:
                    logging.warning(f"Error unregistering mDNS service: {e}")

            if self._zc:
                try:
                    self._zc.close()
                except Exception as e:
                    logging.warning(f"Error closing Zeroconf instance: {e}")

            self._zc = None
            self._service_info = None
            self._is_running = False

    def reload(
        self,
        device_name: str,
        mdns_config: MdnsConfig,
    ) -> bool:
        """Atomically reloads mDNS advertisement with updated settings.

        Args:
            device_name (str): Updated device instance name.
            mdns_config (MdnsConfig): Updated mDNS configuration.

        Returns:
            bool: True if reload succeeded, False otherwise.
        """
        self.stop()
        return self.start(device_name=device_name, mdns_config=mdns_config)


_mdns_service: Optional[MdnsService] = None


def get_mdns_service() -> MdnsService:
    """Returns singleton MdnsService instance.

    Returns:
        MdnsService: Active service instance.
    """
    global _mdns_service
    if _mdns_service is None:
        _mdns_service = MdnsService()
    return _mdns_service
