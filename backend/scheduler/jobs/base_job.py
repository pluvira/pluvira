"""Abstract base class for all background scheduler jobs."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseJob(ABC):
    """Abstract interface defining background job execution contract and metadata."""

    job_id: str = "base_job"
    display_name: str = "Base Job"
    description: str = "Base scheduler job description."
    is_system: bool = False

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Executes the specific job routine asynchronously.

        Args:
            **kwargs (Any): Runtime arguments and contextual filters.

        Returns:
            Any: Optional execution result.
        """
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Returns standard metadata dictionary for UI inspection and schemas.

        Returns:
            Dict[str, Any]: Metadata dictionary.
        """
        return {
            "mode": cls.job_id,
            "display_name": cls.display_name,
            "description": cls.description,
            "is_system": cls.is_system,
        }
