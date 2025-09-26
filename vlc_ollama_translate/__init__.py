"""VLC Ollama Translate package."""

from .config import PluginConfig, load_config, save_config
from .translator import SubtitleTranslator, TranslationResult

__all__ = [
    "PluginConfig",
    "load_config",
    "save_config",
    "SubtitleTranslator",
    "TranslationResult",
]
