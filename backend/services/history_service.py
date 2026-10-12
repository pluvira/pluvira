"""History service layer encapsulating business logic for execution history records in pluvira_main.db."""

from typing import List, Dict, Any, Optional
from backend.core.history import SQLiteHistoryRepository
from backend.core.exceptions import EntityNotFoundError


class HistoryService:
    """Service handling execution history retrieval, deletion, and clearing."""

    def __init__(self, repository: Optional[SQLiteHistoryRepository] = None) -> None:
        """Initializes history service with repository instance.

        Args:
            repository (Optional[SQLiteHistoryRepository]): Override history repository instance.
        """
        self.repository = repository or SQLiteHistoryRepository()

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves all execution history records as dictionaries.

        Returns:
            List[Dict[str, Any]]: List of history record dictionaries.
        """
        records = self.repository.get_all()
        return [record.model_dump() for record in records]

    def delete_record(self, record_id: str) -> None:
        """Deletes a single execution history record by ID.

        Args:
            record_id (str): Unique record ID.

        Raises:
            EntityNotFoundError: If record ID is not found.
        """
        success = self.repository.delete(record_id)
        if not success:
            raise EntityNotFoundError(f"History record '{record_id}' not found.")

    def clear_all_history(self) -> None:
        """Clears all execution history records."""
        self.repository.clear_all()
