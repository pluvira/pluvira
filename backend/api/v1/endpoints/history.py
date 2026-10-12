"""Execution history REST endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, status, Depends

from backend.services.history_service import HistoryService

router = APIRouter()


def get_history_service() -> HistoryService:
    """Dependency provider for HistoryService instance."""
    return HistoryService()


@router.get("", status_code=status.HTTP_200_OK)
def get_execution_history(service: HistoryService = Depends(get_history_service)) -> List[Dict[str, Any]]:
    """Retrieves execution history records.

    Returns:
        List[Dict[str, Any]]: List of history record objects.
    """
    return service.get_history()


@router.delete("/{record_id}", status_code=status.HTTP_200_OK)
def delete_history_record(
    record_id: str, service: HistoryService = Depends(get_history_service)
) -> Dict[str, str]:
    """Deletes a single execution history record by ID.

    Args:
        record_id (str): Record ID to delete.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.delete_record(record_id)
    return {"message": f"History record '{record_id}' deleted successfully."}


@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_history(service: HistoryService = Depends(get_history_service)) -> Dict[str, str]:
    """Clears all execution history records.

    Returns:
        Dict[str, str]: Operation status message.
    """
    service.clear_all_history()
    return {"message": "All execution history cleared successfully."}
