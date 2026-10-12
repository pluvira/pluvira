"""Polite link scanner REST endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, status, BackgroundTasks, Depends

from backend.config.models import (
    TestLinkPayload,
    BatchTestLinkItem,
    BatchTestLinkPayload,
    LinkStatusReportPayload,
)
from backend.services.scanner_service import ScannerService

router = APIRouter()


def get_scanner_service() -> ScannerService:
    """Dependency provider for ScannerService instance."""
    return ScannerService()


@router.post("/test-link", status_code=status.HTTP_200_OK)
async def test_stream_link(
    payload: TestLinkPayload, service: ScannerService = Depends(get_scanner_service)
) -> Dict[str, Any]:
    """Performs real-time HTTP link verification and trace analysis.

    Args:
        payload (TestLinkPayload): Target URL and User-Agent parameters.
        service (ScannerService): ScannerService dependency instance.

    Returns:
        Dict[str, Any]: Link test result with status code and trace logs.
    """
    return await service.test_single_link(payload.url, payload.original_url, payload.user_agent)




@router.post("/test-links-batch", status_code=status.HTTP_202_ACCEPTED)
def trigger_batch_link_test(
    payload: BatchTestLinkPayload,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: ScannerService = Depends(get_scanner_service),
) -> Dict[str, str]:
    """Triggers background batch stream link testing task.

    Args:
        payload (BatchTestLinkPayload): List of link test items.
        background_tasks (BackgroundTasks): FastAPI background tasks dependency.
        service (ScannerService): ScannerService dependency instance.

    Returns:
        Dict[str, str]: Status message.
    """
    items_dict = [item.model_dump() for item in payload.items]
    return service.trigger_batch_link_test(items_dict, background_tasks)


@router.post("/stop", status_code=status.HTTP_200_OK)
def stop_batch_link_test(
    service: ScannerService = Depends(get_scanner_service),
) -> Dict[str, str]:
    """Sends stop signal to abort running batch link test.

    Args:
        service (ScannerService): ScannerService dependency instance.

    Returns:
        Dict[str, str]: Status message.
    """
    return service.stop_batch_link_test()


@router.post("/report-status", status_code=status.HTTP_200_OK)
def report_link_status(
    payload: LinkStatusReportPayload, service: ScannerService = Depends(get_scanner_service)
) -> Dict[str, Any]:
    """Persists stream playback status reported directly by client video player.

    Args:
        payload (LinkStatusReportPayload): Client playback report parameters.
        service (ScannerService): ScannerService dependency instance.

    Returns:
        Dict[str, Any]: Operation status report.
    """
    return service.report_link_status(
        original_url=payload.original_url,
        link_status=payload.link_status,
        code=payload.code,
        cors_supported=payload.cors_supported,
        needs_proxy=payload.needs_proxy,
        error_message=payload.error_message,
        source=payload.source,
        url=payload.url,
    )


@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_link_status_database(
    service: ScannerService = Depends(get_scanner_service),
) -> Dict[str, str]:
    """Resets link status database cache.

    Args:
        service (ScannerService): ScannerService dependency instance.

    Returns:
        Dict[str, str]: Status message.
    """
    return service.reset_status_database()
