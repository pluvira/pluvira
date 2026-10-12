"""Personal channel service layer encapsulating business logic for logical channels and stream slots."""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.config.models import PersonalChannel, ChannelSlot
from backend.core.personal_repository import PersonalPlaylistRepository
from backend.config.settings import settings
from backend.core.db import db_manager
from backend.core.exceptions import (
    EntityNotFoundError,
    PersonalChannelLimitExceeded,
    MaxSlotsExceededError,
)
from backend.core.license_thresholds import LicenseThresholdManager


class PersonalChannelService:
    """Service handling logical personal channels, slot pool management, and suggestion reviews."""

    def __init__(self, repository: Optional[PersonalPlaylistRepository] = None) -> None:
        """Initializes personal channel service and ensures schema exists.

        Args:
            repository (Optional[PersonalPlaylistRepository]): Override personal playlist repository.
        """
        self.repository = repository or PersonalPlaylistRepository(settings.data_dir)

    def get_channels(self, playlist_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieves all personal channels for a given playlist with slots and suggestions.

        Args:
            playlist_id (str): Target playlist ID.

        Returns:
            List[Dict[str, Any]]: List of personal channel dictionaries.
        """
        return self.repository.get_channels(playlist_id)

    def get_channel_by_id(self, channel_id: str) -> Dict[str, Any]:
        """Retrieves a single personal channel by ID with its slots and suggestions.

        Args:
            channel_id (str): Channel unique identifier.

        Returns:
            Dict[str, Any]: Personal channel dictionary.

        Raises:
            EntityNotFoundError: If channel is not found.
        """
        ch = self.repository.get_channel_by_id(channel_id)
        if not ch:
            raise EntityNotFoundError(f"Personal channel with ID '{channel_id}' not found.")
        return ch

    def create_channel(self, payload: PersonalChannel) -> Dict[str, Any]:
        """Creates a new personal channel and its initial slots.

        Args:
            payload (PersonalChannel): Channel payload.

        Returns:
            Dict[str, Any]: Created personal channel dictionary.
        """
        existing_channels = self.get_channels(payload.playlist_id)
        LicenseThresholdManager.validate_curated_channel_count(len(existing_channels) + 1)
        now_str = datetime.now(timezone.utc).isoformat()
        self.repository.insert_channel(payload, now_str)
        return self.get_channel_by_id(payload.id)

    def update_channel(self, channel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates personal channel metadata.

        Args:
            channel_id (str): Channel unique identifier.
            updates (Dict[str, Any]): Dictionary of fields to update.

        Returns:
            Dict[str, Any]: Updated channel dictionary.
        """
        channel = self.get_channel_by_id(channel_id)
        name = updates.get("name", channel["name"])
        logo = updates.get("logo", channel["logo"])
        epg_id = updates.get("epg_id", channel["epg_id"])
        group_name = updates.get("group", channel["group"])
        custom_order = updates.get("custom_order", channel["custom_order"])
        is_pinned = updates.get("is_pinned", channel["is_pinned"])

        self.repository.update_channel_metadata(
            channel_id,
            name=name,
            logo=logo,
            epg_id=epg_id,
            group_name=group_name,
            custom_order=int(custom_order),
            is_pinned=bool(is_pinned),
        )
        return self.get_channel_by_id(channel_id)

    def delete_channel(self, channel_id: str) -> None:
        """Deletes a personal channel and all its slots and suggestions.

        Args:
            channel_id (str): Target channel identifier.
        """
        self.get_channel_by_id(channel_id)
        self.repository.delete_channel(channel_id)

    def toggle_bookmark(
        self, playlist_id: str, channel_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Toggles bookmarking for a channel from the general catalog into a personal playlist.

        Args:
            playlist_id (str): Target personal playlist ID.
            channel_item (Dict[str, Any]): Processed catalog channel item.

        Returns:
            Dict[str, Any]: Status dictionary containing bookmarked boolean and channel_id.
        """
        target_name = channel_item.get("name", "").strip()
        stream_url = channel_item.get("url") or channel_item.get("original_url", "")
        source_name = channel_item.get("source", "Unknown")

        existing_channels = self.get_channels(playlist_id)

        matched_channel = None
        for ch in existing_channels:
            if ch["name"].lower() == target_name.lower():
                matched_channel = ch
                break
            for s in ch["slots"]:
                if s["url"] == stream_url and s["source"] == source_name:
                    matched_channel = ch
                    break
            if matched_channel:
                break

        if matched_channel:
            self.delete_channel(matched_channel["id"])
            return {"bookmarked": False, "channel_id": matched_channel["id"]}

        LicenseThresholdManager.validate_curated_channel_count(len(existing_channels) + 1)
        new_channel_id = f"pch_{uuid.uuid4().hex[:12]}"
        initial_slot = ChannelSlot(
            id=f"slot_{uuid.uuid4().hex[:12]}",
            personal_channel_id=new_channel_id,
            slot_index=0,
            url=stream_url,
            source=source_name,
            user_agent=channel_item.get("user_agent"),
            health_score=100.0,
        )
        new_personal_channel = PersonalChannel(
            id=new_channel_id,
            playlist_id=playlist_id,
            name=target_name or "Unnamed Channel",
            logo=channel_item.get("logo", ""),
            epg_id=channel_item.get("epg_id", ""),
            group=channel_item.get("group", ""),
            slots=[initial_slot],
        )
        self.create_channel(new_personal_channel)
        return {"bookmarked": True, "channel_id": new_channel_id}

    def add_slot(self, personal_channel_id: str, slot: ChannelSlot) -> Dict[str, Any]:
        """Adds a candidate stream slot to a personal channel enforcing the 7-slot cap.

        Args:
            personal_channel_id (str): Target channel identifier.
            slot (ChannelSlot): Stream slot model.

        Returns:
            Dict[str, Any]: Updated channel dictionary.
        """
        channel = self.get_channel_by_id(personal_channel_id)
        current_slots = [ChannelSlot(**s) for s in channel["slots"]]

        current_slots = [s for s in current_slots if s.url != slot.url]
        slot.personal_channel_id = personal_channel_id
        if not slot.id:
            slot.id = f"slot_{uuid.uuid4().hex[:12]}"
        current_slots.append(slot)
        LicenseThresholdManager.validate_slot_count(len(current_slots))

        self.repository.update_channel_slots(personal_channel_id, current_slots)
        return self.get_channel_by_id(personal_channel_id)

    def remove_slot(self, personal_channel_id: str, slot_id: str) -> Dict[str, Any]:
        """Removes a stream slot from a personal channel and re-indexes remaining slots.

        Args:
            personal_channel_id (str): Target channel ID.
            slot_id (str): Slot ID to remove.

        Returns:
            Dict[str, Any]: Updated channel dictionary.
        """
        channel = self.get_channel_by_id(personal_channel_id)
        remaining = [ChannelSlot(**s) for s in channel["slots"] if s["id"] != slot_id]

        self.repository.update_channel_slots(personal_channel_id, remaining)
        return self.get_channel_by_id(personal_channel_id)

    def reorder_slots_manual(self, personal_channel_id: str, slot_ids: List[str]) -> Dict[str, Any]:
        """Manually updates slot_index order for stream slots of a personal channel.

        Args:
            personal_channel_id (str): Target channel identifier.
            slot_ids (List[str]): Ordered list of slot IDs.

        Returns:
            Dict[str, Any]: Updated personal channel dictionary.
        """
        channel = self.get_channel_by_id(personal_channel_id)
        valid_slot_ids = [sid for sid in slot_ids if any(s["id"] == sid for s in channel["slots"])]
        self.repository.update_slot_order(personal_channel_id, valid_slot_ids)
        return self.get_channel_by_id(personal_channel_id)

    def evaluate_and_sync_failover(self, playlist_id: str = "default") -> List[Dict[str, Any]]:
        """Evaluates failover and reorders stream slots delegating to Pro Rust IPC or falling back to Python.

        Args:
            playlist_id (str): Target playlist ID.

        Returns:
            List[Dict[str, Any]]: List of updated personal channel dictionaries.
        """
        from backend.core.pro_bridge import ProBridge

        channels = self.get_channels(playlist_id)
        if not channels:
            return []

        if ProBridge.is_available():
            main_db_path = str(db_manager.get_db_path())
            merged_channels = []
            for pch in channels:
                slots = pch.get("slots", [])
                if not slots:
                    continue
                p_slot = slots[0]
                b_slots = slots[1:]
                merged_channels.append({
                    "channel_id": pch.get("id"),
                    "canonical_name": pch.get("name"),
                    "primary_stream": {
                        "url": p_slot.get("url"),
                        "original_url": p_slot.get("url"),
                        "source": p_slot.get("source"),
                        "user_agent": p_slot.get("user_agent"),
                    },
                    "backup_streams": [
                        {
                            "url": b.get("url"),
                            "original_url": b.get("url"),
                            "source": b.get("source"),
                            "user_agent": b.get("user_agent"),
                        }
                        for b in b_slots
                    ],
                })

            pro_res = ProBridge.execute_sync(
                "evaluate-failover",
                payload={
                    "merged_channels": merged_channels,
                    "personal_channels": channels,
                    "main_db_path": main_db_path,
                },
            )
            if pro_res and isinstance(pro_res, dict) and pro_res.get("status") == "success":
                res_obj = pro_res.get("result") if isinstance(pro_res.get("result"), dict) else pro_res
                updated_channels = res_obj.get("updated_personal_channels") or res_obj.get("updated_merged_channels")
                if updated_channels:
                    self.repository.sync_pro_evaluated_slots(updated_channels)
                    return self.get_channels(playlist_id)

        for pch in channels:
            slots_list = [ChannelSlot(**s) for s in pch.get("slots", [])]
            self.repository.update_channel_slots(pch["id"], slots_list)

        return self.get_channels(playlist_id)

    def approve_suggestion(self, suggestion_id: str) -> Dict[str, Any]:
        """Approves a pending stream suggestion, adding it as a slot and deleting the suggestion.

        Args:
            suggestion_id (str): Suggestion unique identifier.

        Returns:
            Dict[str, Any]: Updated personal channel dictionary.

        Raises:
            EntityNotFoundError: If suggestion is not found.
        """
        sg = self.repository.get_suggestion_by_id(suggestion_id)
        if not sg:
            raise EntityNotFoundError(f"Suggestion with ID '{suggestion_id}' not found.")

        target_chid = sg[1]
        new_slot = ChannelSlot(
            id=f"slot_{uuid.uuid4().hex[:12]}",
            personal_channel_id=target_chid,
            url=sg[2],
            source=sg[3],
            user_agent=sg[4],
            health_score=100.0,
        )
        self.repository.delete_suggestion(suggestion_id)
        return self.add_slot(target_chid, new_slot)

    def reject_suggestion(self, suggestion_id: str) -> None:
        """Rejects and deletes a pending stream suggestion.

        Args:
            suggestion_id (str): Suggestion unique identifier.
        """
        self.repository.delete_suggestion(suggestion_id)
