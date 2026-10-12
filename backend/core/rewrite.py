"""Metadata cascading rewrite engine supporting Channel objects and dictionaries."""

import re
from typing import List, Dict, Optional, Set, Any
from collections import defaultdict

from backend.config.models import RewriteRule, GlobalConfig
from backend.core.models.channel import Channel


class RewriteService:
    """Applies cascading regex, wildcard, text, and replace metadata rules."""

    def __init__(self) -> None:
        """Initializes pattern cache dictionary."""
        self._regex_cache: Dict[str, re.Pattern] = {}
        self._attr_map = {
            "name": "name",
            "group": "group-title",
            "logo": "tvg-logo",
            "url": "url",
            "user_agent": "user_agent",
        }

    def apply_rules(self, channel: Channel, rules: List[RewriteRule]) -> Set[str]:
        """Applies basic replace mode metadata rules directly to a Channel object for Python Core.

        Args:
            channel (Channel): Channel instance to transform.
            rules (List[RewriteRule]): List of rewrite rules to apply.

        Returns:
            Set[str]: Set of attribute keys modified by the rules.
        """
        modified_keys = set()
        if not rules:
            return modified_keys

        for rule in rules:
            if not rule.enabled:
                continue

            attr_key = self._attr_map.get(rule.field, rule.field)
            current_value = channel.get_field(attr_key)

            new_value, changed = self._apply_rule_transformation(current_value, rule)
            if changed:
                modified_keys.add(attr_key)
                self._update_channel_field(channel, attr_key, new_value)

        return modified_keys

    def process_cascading(
        self,
        channel: Channel,
        global_rules: List[RewriteRule],
        source_rules: List[RewriteRule],
        individual_rules: List[RewriteRule],
    ) -> Dict[str, List[str]]:
        """Applies rewrite rules in hierarchical tier precedence (Global -> Source -> Individual).

        Args:
            channel (Channel): Channel instance.
            global_rules (List[RewriteRule]): Global rules tier.
            source_rules (List[RewriteRule]): Source rules tier.
            individual_rules (List[RewriteRule]): Individual channel rules tier.

        Returns:
            Dict[str, List[str]]: Impact dictionary mapping field names to list of impacting tiers.
        """
        field_impact = defaultdict(list)

        for key in self.apply_rules(channel, global_rules):
            field_impact[key].append("Global")

        for key in self.apply_rules(channel, source_rules):
            field_impact[key].append("Source")

        for key in self.apply_rules(channel, individual_rules):
            field_impact[key].append("Individual")

        channel.update_extinf()
        return dict(field_impact)

    def apply_rules_to_dict(self, channel_data: Dict[str, Any], rules: List[RewriteRule]) -> Set[str]:
        """Applies basic replace mode rules directly to a channel dictionary for Python Core."""
        modified_keys = set()
        if not rules:
            return modified_keys

        for rule in rules:
            if not rule.enabled:
                continue

            attr_key = self._attr_map.get(rule.field, rule.field)
            current_value = channel_data.get(attr_key, "")

            new_value, changed = self._apply_rule_transformation(current_value, rule)
            if changed:
                modified_keys.add(attr_key)
                channel_data[attr_key] = new_value

        return modified_keys

    def _apply_rule_transformation(self, current_val: str, rule: RewriteRule) -> tuple[str, bool]:
        """Evaluates and transforms a string value based on rule mode.

        Args:
            current_val (str): Current field string value.
            rule (RewriteRule): RewriteRule configuration.

        Returns:
            tuple[str, bool]: Transformed string value and boolean indicating modification.
        """
        if rule.mode == "replace":
            if rule.replacement != current_val:
                return rule.replacement, True
            return current_val, False

        if not rule.pattern:
            return current_val, False

        compiled = self._get_compiled_regex(rule)
        if not compiled:
            return current_val, False

        if rule.mode == "wildcard":
            if compiled.search(current_val):
                if rule.replacement != current_val:
                    return rule.replacement, True
            return current_val, False

        try:
            new_val = compiled.sub(rule.replacement, current_val)
            if new_val != current_val:
                return new_val, True
        except Exception:
            return current_val, False

        return current_val, False

    def _update_channel_field(self, channel: Channel, attr_key: str, value: str) -> None:
        """Helper to update corresponding field on Channel object.

        Args:
            channel (Channel): Target channel instance.
            attr_key (str): Attribute key name.
            value (str): New value string.
        """
        if attr_key == "name":
            channel.name = value
        elif attr_key == "url":
            channel.url = value
        elif attr_key == "user_agent":
            channel.user_agent = value
        else:
            channel.attributes[attr_key] = value

    def _get_compiled_regex(self, rule: RewriteRule) -> Optional[re.Pattern]:
        """Retrieves or compiles regex pattern for rule.

        Args:
            rule (RewriteRule): Rule instance.

        Returns:
            Optional[re.Pattern]: Compiled pattern or None.
        """
        cache_key = f"{rule.mode}:{rule.pattern}"
        if cache_key not in self._regex_cache:
            try:
                pat = rule.pattern
                if rule.mode == "text":
                    pat = re.escape(pat)
                elif rule.mode == "wildcard":
                    pat = f"^{re.escape(pat).replace(r'\*', '.*').replace(r'\?', '.')}$"
                self._regex_cache[cache_key] = re.compile(pat, re.IGNORECASE)
            except Exception:
                return None
        return self._regex_cache[cache_key]

    @staticmethod
    def update_individual_rewrite(
        config: Optional[GlobalConfig],
        url_key: str,
        field: str,
        original_val: str,
        new_val: str,
        repo: Optional[Any] = None,
    ) -> None:
        """Updates or removes an individual channel rewrite rule in config.

        Args:
            config (GlobalConfig): GlobalConfig instance.
            url_key (str): Original URL identity key.
            field (str): Field to target.
            original_val (str): Original raw value.
            new_val (str): New value to apply.
        """
        if repo is not None:
            val_clean = new_val.strip()
            if val_clean and val_clean != original_val:
                repo.set_rule(url_key, field, val_clean, mode="replace")
            else:
                repo.delete_rule(url_key, field)

        if config is None or not hasattr(config, "individual_rewrites") or not isinstance(config.individual_rewrites, dict):
            if repo is None:
                from backend.core.individual_rewrite_repository import IndividualRewriteRepository

                active_repo = IndividualRewriteRepository()
                val_clean = new_val.strip()
                if val_clean and val_clean != original_val:
                    active_repo.set_rule(url_key, field, val_clean, mode="replace")
                else:
                    active_repo.delete_rule(url_key, field)
            return

        rules = config.individual_rewrites.get(url_key, [])
        rules = [r for r in rules if r.field != field]

        if new_val.strip() and new_val != original_val:
            rules.append(RewriteRule(field=field, mode="replace", replacement=new_val, enabled=True))

        if rules:
            config.individual_rewrites[url_key] = rules
        else:
            config.individual_rewrites.pop(url_key, None)
