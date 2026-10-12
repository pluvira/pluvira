"""Source service layer encapsulating business logic for IPTV M3U and EPG XMLTV sources."""

from typing import List, Dict, Any, Optional
from backend.config.yaml_handler import YAMLConfigHandler
from backend.config.models import Source, EPGSource, SourceSettings
from backend.core.source_repository import SourceRepository
from backend.core.license_thresholds import LicenseThresholdManager
from backend.core.epg_override_repository import EpgOverrideRepository
from backend.core.source_filter_repository import SourceFilterRepository
from backend.core.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    InvalidConfigurationError,
    ProcessLockedError,
)


class SourceService:
    """Service handling CRUD operations and state toggles for IPTV M3U and EPG guide sources."""

    def __init__(
        self,
        config_handler: Optional[YAMLConfigHandler] = None,
        repository: Optional[SourceRepository] = None,
    ) -> None:
        """Initializes source service with configuration handler and source repository.

        Args:
            config_handler (Optional[YAMLConfigHandler]): Override configuration handler instance.
        """
        self.config_handler = config_handler or YAMLConfigHandler()
        self.repository = repository or SourceRepository()
        self.override_repo = EpgOverrideRepository(db_path=self.repository.db_path)
        self.filter_repo = SourceFilterRepository(db_path=self.repository.db_path)

    def get_sources(self) -> List[Dict[str, Any]]:
        """Retrieves configured IPTV M3U sources.

        Returns:
            List[Dict[str, Any]]: List of source model dictionaries.
        """
        sources = self.repository.get_all_sources()
        return [s.model_dump() for s in sources]

    def create_source(self, source_payload: Source) -> Dict[str, Any]:
        """Adds a new IPTV M3U source configuration.

        Args:
            source_payload (Source): Source model payload.

        Returns:
            Dict[str, Any]: Created source dictionary.

        Raises:
            DuplicateEntityError: If a source with the same name already exists.
        """
        if self.repository.get_source(source_payload.name):
            raise DuplicateEntityError(f"Source with name '{source_payload.name}' already exists.")
        if getattr(source_payload, "enabled", True):
            active_count = self.repository.get_active_sources_count() + 1
            LicenseThresholdManager.validate_active_sources(active_count)
        self.repository.save_source(source_payload)

        return source_payload.model_dump()

    def toggle_source_status(self, source_name: str) -> Dict[str, Any]:
        """Toggles enabled status for a specific IPTV M3U source.

        Args:
            source_name (str): IPTV source provider name.

        Returns:
            Dict[str, Any]: Updated source status dictionary.

        Raises:
            EntityNotFoundError: If source name is not found.
        """
        source = self.repository.get_source(source_name)
        if not source:
            raise EntityNotFoundError(f"Source with name '{source_name}' not found.")

        new_enabled = not getattr(source, "enabled", True)
        if new_enabled:
            active_count = self.repository.get_active_sources_count() + 1
            LicenseThresholdManager.validate_active_sources(active_count)
        source.enabled = new_enabled
        self.repository.save_source(source)
        return {
            "name": source.name,
            "enabled": source.enabled,
            "message": f"Source '{source_name}' is now {'enabled' if source.enabled else 'disabled'}.",
        }
    def delete_source(self, source_name: str) -> None:
        """Removes an IPTV M3U source from configuration.

        Args:
            source_name (str): IPTV source provider name.

        Raises:
            EntityNotFoundError: If source name is not found.
        """
        if not self.repository.delete_source(source_name):
            raise EntityNotFoundError(f"Source with name '{source_name}' not found.")

        self.override_repo.delete_by_source(source_name)
        self.filter_repo.delete_by_source(source_name)

    def get_epg_sources(self) -> List[Dict[str, Any]]:
        """Retrieves configured global EPG XMLTV sources.

        Returns:
            List[Dict[str, Any]]: List of EPG source model dictionaries.
        """
        epg_sources = self.repository.get_all_epg_sources()
        return [s.model_dump() for s in epg_sources]

    def create_epg_source(self, epg_source_payload: EPGSource) -> Dict[str, Any]:
        """Adds a new global EPG XMLTV source configuration.

        Args:
            epg_source_payload (EPGSource): EPG source model payload.

        Returns:
            Dict[str, Any]: Created EPG source dictionary.

        Raises:
            DuplicateEntityError: If an EPG source with the same name already exists.
        """
        if self.repository.get_epg_source(epg_source_payload.name):
            raise DuplicateEntityError(f"EPG source with name '{epg_source_payload.name}' already exists.")
        self.repository.save_epg_source(epg_source_payload)

        return epg_source_payload.model_dump()

    def toggle_epg_source_status(self, source_name: str) -> Dict[str, Any]:
        """Toggles enabled status for a specific global EPG source.

        Args:
            source_name (str): EPG guide source name.

        Returns:
            Dict[str, Any]: Updated EPG source status dictionary.

        Raises:
            EntityNotFoundError: If EPG source name is not found.
        """
        epg_src = self.repository.get_epg_source(source_name)
        if not epg_src:
            raise EntityNotFoundError(f"EPG source with name '{source_name}' not found.")

        new_enabled = not getattr(epg_src, "enabled", True)
        epg_src.enabled = new_enabled
        self.repository.save_epg_source(epg_src)
        return {
            "name": epg_src.name,
            "enabled": epg_src.enabled,
            "message": f"EPG source '{source_name}' is now {'enabled' if epg_src.enabled else 'disabled'}.",
        }
    def delete_epg_source(self, source_name: str) -> None:
        """Removes a global EPG XMLTV source from configuration.

        Args:
            source_name (str): EPG guide source name.

        Raises:
            EntityNotFoundError: If EPG source name is not found.
        """
        if not self.repository.delete_epg_source(source_name):
            raise EntityNotFoundError(f"EPG source with name '{source_name}' not found.")




    def _bulk_update_status_generic(self, target_attr: str, source_names: List[str], action: str) -> Dict[str, Any]:
        """Bulk enables, disables, or toggles status for multiple sources.

        Args:
            target_attr (str): Configuration attribute name ('sources' or 'epg_sources').
            source_names (List[str]): List of target source names.
            action (str): Action string ('enable', 'disable', 'toggle').

        Returns:
            Dict[str, Any]: Result summary dictionary.
        """
        act = action.lower().strip()
        if act not in ["enable", "disable", "toggle"]:
            raise InvalidConfigurationError(f"Invalid action '{action}'. Must be 'enable', 'disable', or 'toggle'.")
        names_set = set(source_names)
        if target_attr == "sources":
            for name in names_set:
                src = self.repository.get_source(name)
                if src:
                    if act == "enable":
                        src.enabled = True
                    elif act == "disable":
                        src.enabled = False
                    elif act == "toggle":
                        src.enabled = not getattr(src, "enabled", True)
                    self.repository.save_source(src)
        else:
            for name in names_set:
                epg = self.repository.get_epg_source(name)
                if epg:
                    if act == "enable":
                        epg.enabled = True
                    elif act == "disable":
                        epg.enabled = False
                    elif act == "toggle":
                        epg.enabled = not getattr(epg, "enabled", True)
                    self.repository.save_epg_source(epg)

        return {"updated_count": len(names_set), "message": f"Bulk status action '{act}' applied to {len(names_set)} sources."}

    def bulk_update_source_status(self, source_names: List[str], action: str) -> Dict[str, Any]:
        """Bulk enables, disables, or toggles status for multiple IPTV M3U sources."""
        return self._bulk_update_status_generic("sources", source_names, action)

    def bulk_update_epg_source_status(self, source_names: List[str], action: str) -> Dict[str, Any]:
        """Bulk enables, disables, or toggles status for multiple global EPG sources."""
        return self._bulk_update_status_generic("epg_sources", source_names, action)

    def _bulk_delete_generic(self, target_attr: str, source_names: List[str]) -> Dict[str, Any]:
        """Removes multiple sources from configuration in bulk."""
        names_set = set(source_names)
        deleted_count = 0

        if target_attr == "sources":
            for name in names_set:
                if self.repository.delete_source(name):
                    deleted_count += 1
        else:
            for name in names_set:
                if self.repository.delete_epg_source(name):
                    deleted_count += 1

        if target_attr == "sources":
            from backend.core.epg_override_repository import EpgOverrideRepository
            from backend.core.source_filter_repository import SourceFilterRepository
            override_repo = EpgOverrideRepository()
            filter_repo = SourceFilterRepository()
            for name in names_set:
                override_repo.delete_by_source(name)
                filter_repo.delete_by_source(name)
        return {"deleted_count": deleted_count, "message": f"Successfully deleted {deleted_count} sources."}

    def bulk_delete_sources(self, source_names: List[str]) -> Dict[str, Any]:
        """Removes multiple IPTV M3U sources from configuration in bulk."""
        return self._bulk_delete_generic("sources", source_names)

    def bulk_delete_epg_sources(self, source_names: List[str]) -> Dict[str, Any]:
        """Removes multiple global EPG sources from configuration in bulk."""
        return self._bulk_delete_generic("epg_sources", source_names)

    def _bulk_update_user_agent_generic(self, target_attr: str, source_names: List[str], user_agent: str) -> Dict[str, Any]:
        """Updates or resets User-Agent in bulk for multiple sources."""
        from backend.config.models import SourceSettings
        names_set = set(source_names)
        ua_val = user_agent.strip()

        if target_attr == "sources":
            for name in names_set:
                s = self.repository.get_source(name)
                if s:
                    if not s.settings:
                        s.settings = SourceSettings()
                    s.settings.user_agent = ua_val if ua_val else None
                    self.repository.save_source(s)
        else:
            for name in names_set:
                epg = self.repository.get_epg_source(name)
                if epg:
                    epg.user_agent = ua_val if ua_val else None
                    self.repository.save_epg_source(epg)

        return {"updated_count": len(names_set), "message": f"Bulk User-Agent updated for {len(names_set)} sources."}

    def bulk_update_source_user_agent(self, source_names: List[str], user_agent: str) -> Dict[str, Any]:
        """Updates or resets User-Agent in bulk for multiple IPTV M3U sources."""
        return self._bulk_update_user_agent_generic("sources", source_names, user_agent)

    def bulk_update_epg_source_user_agent(self, source_names: List[str], user_agent: str) -> Dict[str, Any]:
        """Updates or resets User-Agent in bulk for multiple global EPG sources."""
        return self._bulk_update_user_agent_generic("epg_sources", source_names, user_agent)

    def _bulk_reorder_generic(self, target_attr: str, ordered_names: List[str]) -> Dict[str, Any]:
        """Reorders sources sequentially based on the provided names list."""
        if target_attr == "sources":
            self.repository.reorder_sources(ordered_names)
        else:
            self.repository.reorder_epg_sources(ordered_names)

        return {"message": "Sources reordered successfully."}

    def bulk_reorder_sources(self, ordered_names: List[str]) -> Dict[str, Any]:
        """Reorders IPTV M3U sources based on the provided sequential list of names."""
        return self._bulk_reorder_generic("sources", ordered_names)

    def bulk_reorder_epg_sources(self, ordered_names: List[str]) -> Dict[str, Any]:
        """Reorders global EPG sources based on the provided sequential list of names."""
        return self._bulk_reorder_generic("epg_sources", ordered_names)

    def _dispatch_selective_refresh(self, mode: str, source_names: List[str], background_tasks: Any) -> Dict[str, str]:
        """Triggers background acquisition refresh for specific sources."""
        from backend.services.system_service import SystemService

        system_service = SystemService(config_handler=self.config_handler)
        if system_service.is_running():
            raise ProcessLockedError("System update process is already running.")

        background_tasks.add_task(system_service.run_selective_refresh_task, mode, source_names)
        return {"message": f"Selective refresh started for {len(source_names)} {mode.upper()} sources."}

    def bulk_refresh_sources(self, source_names: List[str], background_tasks: Any) -> Dict[str, str]:
        """Triggers background acquisition refresh for specific M3U sources."""
        return self._dispatch_selective_refresh("m3u", source_names, background_tasks)

    def bulk_refresh_epg_sources(self, source_names: List[str], background_tasks: Any) -> Dict[str, str]:
        """Triggers background acquisition refresh for specific EPG sources."""
        return self._dispatch_selective_refresh("epg", source_names, background_tasks)
