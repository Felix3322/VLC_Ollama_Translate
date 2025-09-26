"""Configuration management for the VLC Ollama Translate plugin.

This module mirrors the behaviour of the PotPlayer ChatGPT plugin
configuration system.  The PotPlayer version stored configuration
values inside PotPlayer's registry like storage.  For the VLC port we
persist the data on disk as JSON while keeping the same defaults and
parsing logic so that the rest of the translation pipeline can be
ported almost line-for-line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path.home() / ".config" / "vlc_ollama_translate"
CONFIG_FILE = CONFIG_DIR / "config.json"


DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_DELAY_MS = 0
DEFAULT_RETRY_MODE = 0
DEFAULT_CONTEXT_TOKEN_BUDGET = 6000
DEFAULT_CONTEXT_TRUNCATION_MODE = "drop_oldest"
DEFAULT_CONTEXT_CACHE_MODE = "auto"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Matches the logic in the PotPlayer plugin where installer supplied
# token rules can override defaults.  The structure mirrors
# ``pre_model_token_limits_json`` which is a JSON object with two keys:
# ``default`` and ``rules``.  ``rules`` is a list of dictionaries with
# ``type`` (``prefix``/``contains``/``equals``), ``value`` and
# ``tokens``.
DEFAULT_TOKEN_LIMIT_RULES = {
    "default": 4096,
    "rules": [
        {"type": "contains", "value": "gpt-4", "tokens": 8192},
        {"type": "contains", "value": "gpt-4o", "tokens": 128000},
        {"type": "contains", "value": "gpt-4.1", "tokens": 128000},
        {"type": "contains", "value": "gpt-4o-mini", "tokens": 128000},
        {"type": "contains", "value": "gpt-5", "tokens": 128000},
        {"type": "contains", "value": "o1", "tokens": 128000},
        {"type": "contains", "value": "gemini", "tokens": 122880},
    ],
}


@dataclass
class PluginConfig:
    """Configuration container for the VLC port.

    The fields intentionally mirror the names used by the PotPlayer
    plugin so that the translation logic can be ported with minimal
    changes.
    """

    api_key: str = ""
    selected_model: str = DEFAULT_MODEL
    api_url: str = DEFAULT_API_URL
    delay_ms: int = DEFAULT_DELAY_MS
    retry_mode: int = DEFAULT_RETRY_MODE
    context_token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET
    context_truncation_mode: str = DEFAULT_CONTEXT_TRUNCATION_MODE
    context_cache_mode: str = DEFAULT_CONTEXT_CACHE_MODE
    model_token_limits: Dict[str, Any] = field(
        default_factory=lambda: json.loads(json.dumps(DEFAULT_TOKEN_LIMIT_RULES))
    )
    user_agent: str = DEFAULT_USER_AGENT
    source_language: str = ""
    target_language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_key": self.api_key,
            "selected_model": self.selected_model,
            "api_url": self.api_url,
            "delay_ms": self.delay_ms,
            "retry_mode": self.retry_mode,
            "context_token_budget": self.context_token_budget,
            "context_truncation_mode": self.context_truncation_mode,
            "context_cache_mode": self.context_cache_mode,
            "model_token_limits": self.model_token_limits,
            "user_agent": self.user_agent,
            "source_language": self.source_language,
            "target_language": self.target_language,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginConfig":
        cfg = cls()
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        # Normalise fields that should be integers.
        cfg.delay_ms = int(cfg.delay_ms)
        cfg.retry_mode = int(cfg.retry_mode)
        cfg.context_token_budget = int(cfg.context_token_budget)
        return cfg

    def save(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = CONFIG_FILE
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PluginConfig":
        if path is None:
            path = CONFIG_FILE
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    def update_from_login_string(self, login_string: str) -> None:
        """Mimic the PotPlayer login parsing logic.

        The login text in the PotPlayer plugin is in the form
        ``model|api_url|nullkey|delay|retry|cache``.  ``nullkey`` tells
        the plugin that the API does not require authentication.  We
        reproduce the same behaviour so the documentation and user
        expectations remain valid after porting to VLC.
        """

        tokens = [token.strip() for token in login_string.split("|") if token.strip()]
        if not tokens:
            return
        self.selected_model = tokens[0]
        for token in tokens[1:]:
            lowered = token.lower()
            if lowered.startswith("http://") or lowered.startswith("https://"):
                self.api_url = token
            elif lowered == "nullkey":
                # Leaving api_key empty signals that authentication is not
                # required.
                self.api_key = ""
            elif lowered.startswith("delay="):
                try:
                    self.delay_ms = int(lowered.split("=", 1)[1])
                except ValueError:
                    self.delay_ms = DEFAULT_DELAY_MS
            elif lowered.startswith("retry"):
                digits = ''.join(ch for ch in lowered if ch.isdigit())
                if digits:
                    self.retry_mode = int(digits)
            elif lowered.startswith("cache="):
                mode = token.split("=", 1)[1].strip().lower()
                if mode in {"auto", "off", "disable", "disabled", "chat"}:
                    self.context_cache_mode = "off" if mode != "auto" else "auto"
                else:
                    self.context_cache_mode = DEFAULT_CONTEXT_CACHE_MODE
            elif lowered.isdigit():
                value = int(lowered)
                # Heuristic: values greater than 1000 are most likely a
                # delay configuration; otherwise assume retry mode.
                if value >= 1000:
                    self.delay_ms = value
                else:
                    self.retry_mode = value

    def normalise_languages(self) -> None:
        if self.source_language in {"", "auto", "auto detect", "auto_detect"}:
            self.source_language = ""
        self.target_language = self.target_language or "en"


def load_config() -> PluginConfig:
    return PluginConfig.load()


def save_config(cfg: PluginConfig) -> None:
    cfg.save()
