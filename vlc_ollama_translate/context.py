"""Context management utilities used by the translation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List


def estimate_token_count(text: str) -> int:
    """Rudimentary token estimator.

    The PotPlayer plugin divides the character length by four to
    approximate the token usage which is good enough for budget
    calculations.  We reuse the exact same heuristic here.
    """

    if not text:
        return 0
    return max(0, int(len(text) / 4))


@dataclass
class SubtitleHistory:
    """Maintains recent subtitle lines for contextual translation."""

    entries: List[str] = field(default_factory=list)

    def add(self, subtitle: str) -> None:
        if subtitle:
            self.entries.append(subtitle)

    def shrink(self, target: int) -> None:
        if target < 0:
            target = 0
        if len(self.entries) > target:
            del self.entries[0 : len(self.entries) - target]

    def iter_recent(self) -> Iterable[str]:
        return reversed(self.entries[:-1]) if len(self.entries) > 1 else []


@dataclass
class ContextWindow:
    token_budget: int
    truncation_mode: str = "drop_oldest"

    def build_segments(self, history: SubtitleHistory, current_text: str, max_model_tokens: int) -> List[str]:
        current_tokens = estimate_token_count(current_text)
        safe_budget = max_model_tokens - 1000
        if safe_budget < 0:
            safe_budget = max_model_tokens
        available = max(0, min(self.token_budget, max(0, safe_budget - current_tokens)))
        use_smart_trim = self.truncation_mode.lower() == "smart_trim"

        segments: List[str] = []
        used_tokens = 0
        for subtitle in history.iter_recent():
            tokens = estimate_token_count(subtitle)
            if tokens <= 0:
                continue
            if used_tokens + tokens <= available:
                segments.insert(0, subtitle)
                used_tokens += tokens
            elif use_smart_trim and available > used_tokens:
                remaining = available - used_tokens
                char_budget = remaining * 4
                if char_budget > 0:
                    segments.insert(0, subtitle[-char_budget:])
                break
            else:
                break
        return segments

    def shrink_history(self, history: SubtitleHistory) -> None:
        history_budget = self.token_budget if self.token_budget > 0 else 0
        history_target = int(history_budget / 16) if history_budget else 0
        if history_target < 96:
            history_target = 96
        if history_target > 2048:
            history_target = 2048
        shrink_target = history_target - 64
        if shrink_target < 64:
            shrink_target = history_target // 2 if history_target else 0
        if shrink_target < 32:
            shrink_target = 32
        history.shrink(shrink_target)
