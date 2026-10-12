"""Services package for backend business logic layer."""

from backend.services.channel_service import ChannelService
from backend.services.source_service import SourceService
from backend.services.merge_service import MergeService
from backend.services.history_service import HistoryService
from backend.services.auth_service import AuthService
from backend.services.config_service import ConfigService
from backend.services.system_service import SystemService
from backend.services.scanner_service import ScannerService
from backend.services.epg_service import EpgService
from backend.services.export_service import ExportService
from backend.services.notification_service import NotificationService
from backend.services.analytics_service import AnalyticsService
from backend.services.scheduler_service import SchedulerService
from backend.services.stream_service import StreamService
from backend.services.backup_service import BackupService
from backend.services.playlist_service import PlaylistService
from backend.services.personal_channel_service import PersonalChannelService
from backend.services.purge_service import PurgeService
from backend.services.cloud_pairing_service import CloudPairingService
from backend.services.metadata_service import MetadataService
from backend.services.mdns_service import MdnsService, get_mdns_service

__all__ = [
    "ChannelService",
    "SourceService",
    "MergeService",
    "HistoryService",
    "AuthService",
    "ConfigService",
    "SystemService",
    "ScannerService",
    "EpgService",
    "ExportService",
    "NotificationService",
    "AnalyticsService",
    "SchedulerService",
    "StreamService",
    "BackupService",
    "PlaylistService",
    "PersonalChannelService",
    "PurgeService",
    "CloudPairingService",
    "MetadataService",
    "MdnsService",
    "get_mdns_service",
]
