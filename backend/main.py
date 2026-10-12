"""FastAPI application entrypoint for the headless backend."""

import os
import logging
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.core.spa import setup_spa_static_mount

from backend import __version__
from backend.api.v1.endpoints.health import router as health_router
from backend.api.v1.router import api_v1_router
from backend.core.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidConfigurationError,
    ProcessLockedError,
    LicenseThresholdExceededError,
    PersonalChannelLimitExceeded,
    AuthenticationError,
    BadGatewayError,
    ValidationDomainError,
    MetadataLookupError,
    SystemJobImmutableError,
)
from backend.config.settings import settings
from backend.scheduler.manager import scheduler_manager
from backend.core.notifier import Notifier
from backend.core.pro_bridge import ProBridge
from backend.utils.logger import setup_ui_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown lifecycle events."""
    setup_ui_logger()
    logging.info("Initializing Pluvira Headless API Daemon...")
    os.makedirs(settings.temp_dir, exist_ok=True)

    try:
        from backend.core.lock_manager import LockManager
        LockManager().release()
    except Exception as e:
        logging.warning(f"Failed to reset startup lock file: {e}")

    edition_info = ProBridge.get_edition_info(force_refresh=True)
    if edition_info["edition"] == "pro":
        logging.info(f"🚀 Pluvira running in [PRO EDITION] (Rust IPC Active, License Valid) - v{__version__}")
    else:
        logging.info(f"ℹ️ Pluvira running in [CORE EDITION] ({edition_info['message']}) - v{__version__}")

    mock_status = (
        os.getenv("MOCK_PRO_LICENSE_STATUS")
        or os.getenv("PLUVIRA_MOCK_PRO_LICENSE_STATUS")
        or "N/A"
    )
    lic_info = edition_info.get("license") if isinstance(edition_info, dict) else {}
    if not isinstance(lic_info, dict):
        lic_info = {}
    lic_status = lic_info.get("license_status", "N/A")
    lic_subject = lic_info.get("subject", "N/A")
    lic_days = lic_info.get("days_remaining", "N/A")

    logging.info(f"config: IP_ADDRESS: {settings.api_host}")
    logging.info(f"config: PRT: {settings.api_port}")
    logging.info(f"config: CONFIG_DIR: {settings.config_dir}")
    logging.info(f"config: DATA_DIR: {settings.data_dir}")
    logging.info(f"config: TEMP_DIR: {settings.temp_dir}")
    logging.info(f"config: PRO_BINARY_PATH: {settings.pro_binary_path}")
    logging.info(f"config: CONFIG_FILE_NAME: {settings.config_file_name}")
    logging.info(f"config: SCHEDULE_FILE_NAME: {settings.schedule_file_name}")
    logging.info(f"config: STORAGE_SECRET: {'***' if settings.storage_secret else 'N/A'}")
    logging.info(f"config: MOCK_PRO_LICENSE_STATUS: {mock_status}")
    logging.info(f"config: EDITION: {edition_info.get('edition', 'core')}")
    logging.info(f"config: PRO_ACTIVE: {edition_info.get('pro_active', False)}")
    logging.info(f"config: LICENSE_VALID: {edition_info.get('license_valid', False)}")
    logging.info(f"config: LICENSE_STATUS: {lic_status}")
    logging.info(f"config: LICENSE_SUBJECT: {lic_subject}")
    logging.info(f"config: LICENSE_DAYS_REMAINING: {lic_days}")
    pro_ver = edition_info.get("pro_version") or lic_info.get("pro_version", "N/A")
    update_rec = edition_info.get("update_recommended", False) or lic_info.get("update_recommended", False)
    logging.info(f"config: PRO_VERSION: {pro_ver}")
    logging.info(f"config: UPDATE_RECOMMENDED: {update_rec}")

    notifier = Notifier.from_config()
    notifier.dispatch_event(
        event_name="service_lifecycle_event",
        title="🟢 Pluvira: Service Started",
        body=f"Pluvira daemon v{__version__} [{edition_info['edition'].upper()} EDITION] started successfully.",
        severity="info",
    )

    try:
        scheduler_manager.load_schedule()
        scheduler_manager.start()
    except Exception as e:
        logging.error(f"Failed to initialize scheduler: {e}")

    try:
        from backend.services.mdns_service import get_mdns_service
        get_mdns_service().start()
    except Exception as e:
        logging.warning(f"Failed to start mDNS service: {e}")

    yield

    logging.info("Shutting down Pluvira Headless API Daemon...")
    notifier.dispatch_event(
        event_name="service_lifecycle_event",
        title="🔴 Pluvira: Service Stopped",
        body=f"Pluvira daemon v{__version__} is shutting down.",
        severity="info",
    )
    scheduler_manager.shutdown()
    try:
        from backend.services.mdns_service import get_mdns_service
        get_mdns_service().stop()
    except Exception as e:
        logging.warning(f"Failed to stop mDNS service: {e}")
    if os.path.exists(settings.temp_dir):
        shutil.rmtree(settings.temp_dir, ignore_errors=True)


def create_application() -> FastAPI:
    """Creates and configures the main FastAPI application instance.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(
        title="Pluvira API",
        version=__version__,
        description="Modular IPTV playlist, EPG, and media management suite backend.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DuplicateEntityError)
    async def duplicate_entity_handler(request: Request, exc: DuplicateEntityError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InvalidConfigurationError)
    async def invalid_config_handler(request: Request, exc: InvalidConfigurationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(MetadataLookupError)
    async def metadata_lookup_handler(request: Request, exc: MetadataLookupError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValidationDomainError)
    async def validation_domain_handler(request: Request, exc: ValidationDomainError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BadGatewayError)
    async def bad_gateway_handler(request: Request, exc: BadGatewayError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ProcessLockedError)
    async def process_locked_handler(request: Request, exc: ProcessLockedError):
        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PersonalChannelLimitExceeded)
    async def personal_channel_limit_handler(request: Request, exc: PersonalChannelLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "PERSONAL_CHANNEL_LIMIT_EXCEEDED"},
        )

    @app.exception_handler(LicenseThresholdExceededError)
    async def license_threshold_handler(request: Request, exc: LicenseThresholdExceededError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "FREE_TIER_LIMIT_EXCEEDED"},
        )

    @app.exception_handler(SystemJobImmutableError)
    async def system_job_immutable_handler(request: Request, exc: SystemJobImmutableError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "code": "SYSTEM_JOB_IMMUTABLE"},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logging.error(f"Unhandled API Error on {request.url}: {exc}", exc_info=True)
        try:
            notifier = Notifier.from_config()
            notifier.dispatch_event(
                event_name="api_error_500",
                title="🔴 Pluvira: API Internal Error",
                body=f"Unhandled exception on {request.method} {request.url}.\nError: {exc}",
                severity="critical",
            )
        except Exception as e:
            logging.error(f"Failed to send API error notification: {e}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error. Notification dispatched to administrator."},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(api_v1_router, prefix="/api/v1")
    setup_spa_static_mount(app)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        reload_dirs=["backend"],
        reload_includes=[".env"],
    )
