"""Dashboard analytics REST API endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, status, Depends

from backend.services.analytics_service import AnalyticsService

router = APIRouter()


def get_analytics_service() -> AnalyticsService:
    """Dependency provider for AnalyticsService instance."""
    return AnalyticsService()


@router.get("/dashboard", status_code=status.HTTP_200_OK)
def get_dashboard_analytics(
    service: AnalyticsService = Depends(get_analytics_service),
) -> Dict[str, Any]:
    """Calculates and retrieves global, per-source, and EPG analytics for dashboard.

    Returns:
        Dict[str, Any]: Analytics payload containing sources_stats, global_stats, and epg_sources_stats.
    """
    return service.get_dashboard_analytics()
