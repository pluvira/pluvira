"""Analytics service layer encapsulating business logic for dashboard metrics."""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from backend.config.settings import settings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.processor import DataProcessor
from backend.core.analytics import AnalyticsCalculator
from backend.core.source_repository import SourceRepository
from backend.core.history import SQLiteHistoryRepository
from backend.core.raw_database import RawDatabaseService


class AnalyticsService:
    """Service handling dashboard analytics calculation and orchestration."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        processor: Optional[DataProcessor] = None,
        source_repository: Optional[SourceRepository] = None,
        history_repository: Optional[SQLiteHistoryRepository] = None,
        raw_db_service: Optional[RawDatabaseService] = None,
    ) -> None:
        """Initializes analytics service.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
            processor (Optional[DataProcessor]): Override data processor instance.
            source_repository (Optional[SourceRepository]): Override source repository instance.
            history_repository (Optional[SQLiteHistoryRepository]): Override history repository instance.
            raw_db_service (Optional[RawDatabaseService]): Override raw database service instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.processor = processor or DataProcessor()
        self.source_repo = source_repository or SourceRepository()
        self.history_repo = history_repository or SQLiteHistoryRepository()
        self.raw_db_service = raw_db_service or RawDatabaseService(
            data_dir=settings.data_dir, temp_dir=settings.temp_dir
        )

    def get_dashboard_analytics(self) -> Dict[str, Any]:
        """Calculates and retrieves global, per-source, and EPG analytics via SourceRepository.

        Returns:
            Dict[str, Any]: Analytics payload containing sources_stats, global_stats, and epg_sources_stats.

        Raises:
            HTTPException: 500 Internal Server Error if calculation fails.
        """
        try:
            config = self.config_handler.load_config()
            processed = self.processor.get_processed_channels(config=config)

            sources = self.source_repo.get_all_sources() or (
                config.sources if config and hasattr(config, "sources") else []
            )
            epg_sources = self.source_repo.get_all_epg_sources() or (
                getattr(config, "epg_sources", []) if config else []
            )
            epg_index = self.raw_db_service.load_existing_epg_index()
            raw_epg = self.raw_db_service.load_existing_raw_epg()
            latest_history = self.history_repo.get_latest()

            sources_stats, global_stats, epg_stats = AnalyticsCalculator.calculate_dashboard_analytics(
                processed=processed,
                config=config,
                sources=sources,
                epg_sources=epg_sources,
                epg_index=epg_index,
                raw_epg=raw_epg,
                latest_history=latest_history,
            )

            return {
                "sources_stats": sources_stats,
                "global_stats": global_stats,
                "epg_sources_stats": epg_stats,
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate dashboard analytics: {e}",
            )
