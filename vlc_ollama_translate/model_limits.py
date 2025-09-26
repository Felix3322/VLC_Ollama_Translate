"""Model token limit helpers."""

from __future__ import annotations

from typing import Dict

from .config import PluginConfig


def get_model_max_tokens(config: PluginConfig) -> int:
    rules = config.model_token_limits or {}
    default = int(rules.get("default", 4096))
    model_name = (config.selected_model or "").strip()
    if not model_name:
        return default

    for entry in rules.get("rules", []):
        if not isinstance(entry, dict):
            continue
        rule_type = entry.get("type")
        value = entry.get("value", "")
        limit = int(entry.get("tokens", 0) or 0)
        if limit <= 0 or not value:
            continue
        if rule_type == "prefix" and model_name.startswith(value):
            return limit
        if rule_type == "contains" and value in model_name:
            return limit
        if rule_type == "equals" and model_name == value:
            return limit
    return default
