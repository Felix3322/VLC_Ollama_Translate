"""High level translation service for VLC Ollama Translate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .api_client import APIClient, APIError
from .config import PluginConfig
from .context import ContextWindow, SubtitleHistory


SYSTEM_PROMPT = (
    "You are an expert subtitle translate tool with a deep understanding of both language and culture."
    "Based on contextual clues, you provide translations that capture not only the literal meaning but also the nuanced metaphors,"
    " euphemisms, and cultural symbols embedded in the dialogue."
    "Your translations reflect the intended tone and cultural context, ensuring that every subtle reference and idiomatic expression"
    " is accurately conveyed."
    "I will provide you with some context for better translations, but DO NOT output any of them.\n"
    "Rules:\n"
    "1. Output the translation only.\n"
    "2. Do NOT output extra comments or explanations.\n"
    "3. Do NOT use any special characters or formatting in the translation."
)

CACHE_INSTRUCTION_TEMPLATE = (
    "Translate the complete content under 'Subtitle to translate' using the provided context entries if available. "
    "Each entry is shown as \"Context entry (older to newer): {...}\" and must never appear in the output.\n\n"
    "Source language: {source}\n"
    "Target language: {target}\n\n"
    "Output only the translated subtitle without extra commentary."
)

USER_PROMPT_TEMPLATE = (
    "Translate the complete content under the section 'Subtitle to translate' based on the section 'Subtitle context', if it exists.\n\n"
    "Source language: {source}\n"
    "Target language: {target}\n\n"
    "[Subtitle context](DO NOT OUTPUT!):\n{{{context}}}\n\n"
    "[Subtitle to translate]:\n{{{subtitle}}}"
)


@dataclass
class TranslationResult:
    original: str
    translated: str


class SubtitleTranslator:
    def __init__(self, config: PluginConfig, max_model_tokens: int):
        self.config = config
        self.history = SubtitleHistory()
        self.context_window = ContextWindow(
            token_budget=config.context_token_budget,
            truncation_mode=config.context_truncation_mode,
        )
        self.max_model_tokens = max_model_tokens
        self.client = APIClient(
            api_url=config.api_url,
            api_key=config.api_key,
            model=config.selected_model,
            user_agent=config.user_agent,
            delay_ms=config.delay_ms,
            retry_mode=config.retry_mode,
            context_cache_mode=config.context_cache_mode,
        )
        self._cache_failed = False

    def _format_language(self, value: str, label: str) -> str:
        if not value:
            return label
        return value

    def _build_user_prompt(self, subtitle: str, context_segments: List[str], source: str, target: str) -> str:
        context_text = "\n".join(context_segments) if context_segments else ""
        user_prompt = USER_PROMPT_TEMPLATE.format(
            source=source,
            target=target,
            context=context_text,
            subtitle=subtitle,
        )
        if not context_segments:
            user_prompt = user_prompt.replace("[Subtitle context](DO NOT OUTPUT!):\n{{{context}}}\n\n", "")
        return user_prompt

    def translate(self, subtitle: str) -> TranslationResult:
        self.history.add(subtitle)
        context_segments = self.context_window.build_segments(
            self.history, subtitle, self.max_model_tokens
        )
        self.context_window.shrink_history(self.history)

        source_label = self._format_language(self.config.source_language, "Auto Detect")
        target_label = self._format_language(self.config.target_language, "Auto Detect")

        user_prompt = self._build_user_prompt(subtitle, context_segments, source_label, target_label)
        caching_instruction = CACHE_INSTRUCTION_TEMPLATE.format(
            source=source_label,
            target=target_label,
        )

        translation: Optional[str] = None
        if self.config.context_cache_mode != "off" and not self._cache_failed:
            try:
                translation = self.client.translate_responses(
                    SYSTEM_PROMPT,
                    caching_instruction,
                    context_segments,
                    subtitle,
                )
            except APIError:
                translation = None
                self._cache_failed = True
            else:
                if translation is None:
                    self._cache_failed = True

        if translation is None:
            translation = self.client.translate_chat(SYSTEM_PROMPT, user_prompt)

        if self.config.target_language in {"fa", "ar", "he"}:
            translation = "\u202B" + translation

        return TranslationResult(original=subtitle, translated=translation.strip())
