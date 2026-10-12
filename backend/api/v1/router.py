"""Main API v1 router aggregator."""

from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.api.v1.endpoints.health import router as health_router
from backend.api.v1.endpoints.system import router as system_router
from backend.api.v1.endpoints.config import router as config_router
from backend.api.v1.endpoints.channels import router as channels_router
from backend.api.v1.endpoints.epg import router as epg_router
from backend.api.v1.endpoints.merge import router as merge_router
from backend.api.v1.endpoints.scanner import router as scanner_router
from backend.api.v1.endpoints.history import router as history_router
from backend.api.v1.endpoints.export import router as export_router
from backend.api.v1.endpoints.stream import router as stream_router
from backend.api.v1.endpoints.analytics import router as analytics_router
from backend.api.v1.endpoints.scheduler import router as scheduler_router
from backend.api.v1.endpoints.sources import router as sources_router
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.backup import router as backup_router
from backend.api.v1.endpoints.playlists import router as playlists_router
from backend.api.v1.endpoints.personal_channels import router as personal_channels_router
from backend.api.v1.endpoints.cloud import router as cloud_router
from backend.api.v1.endpoints.metadata import router as metadata_router

auth_deps = [Depends(get_current_user)]

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, prefix="/health", tags=["Health"])
api_v1_router.include_router(export_router, prefix="/export", tags=["Exports"])
api_v1_router.include_router(stream_router, prefix="/stream", tags=["Stream"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Protected admin routers
api_v1_router.include_router(system_router, prefix="/system", tags=["System"], dependencies=auth_deps)
api_v1_router.include_router(config_router, prefix="/config", tags=["Configuration"], dependencies=auth_deps)
api_v1_router.include_router(channels_router, prefix="/channels", tags=["Channels"], dependencies=auth_deps)
api_v1_router.include_router(sources_router, prefix="/sources", tags=["Sources"], dependencies=auth_deps)
api_v1_router.include_router(epg_router, prefix="/epg", tags=["EPG"], dependencies=auth_deps)
api_v1_router.include_router(merge_router, prefix="/merge", tags=["Merge"], dependencies=auth_deps)
api_v1_router.include_router(scanner_router, prefix="/scanner", tags=["Scanner"], dependencies=auth_deps)
api_v1_router.include_router(history_router, prefix="/history", tags=["History"], dependencies=auth_deps)
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"], dependencies=auth_deps)
api_v1_router.include_router(scheduler_router, prefix="/scheduler", tags=["Scheduler"], dependencies=auth_deps)
api_v1_router.include_router(backup_router, prefix="/backup", tags=["Backup"], dependencies=auth_deps)
api_v1_router.include_router(playlists_router, prefix="/playlists", tags=["Playlists"], dependencies=auth_deps)
api_v1_router.include_router(personal_channels_router, prefix="/personal-channels", tags=["PersonalChannels"], dependencies=auth_deps)
api_v1_router.include_router(cloud_router, prefix="/cloud", tags=["Cloud"], dependencies=auth_deps)
api_v1_router.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
