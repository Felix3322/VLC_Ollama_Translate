"""Subtitle parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List


SRT_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*\d+\s*\n"
    r"(?P<start>\d\d:\d\d:\d\d,\d\d\d)\s+-->\s+"
    r"(?P<end>\d\d:\d\d:\d\d,\d\d\d)\s*\n"
    r"(?P<text>(?:.*?(?:\n|$))+?)"
    r"(?=\n\s*\n|\Z)",
    re.DOTALL,
)


@dataclass
class SubtitleEntry:
    start: str
    end: str
    text: str

    def normalised_text(self) -> str:
        return self.text.replace("\r", "").strip()


def parse_srt(content: str) -> List[SubtitleEntry]:
    entries: List[SubtitleEntry] = []
    for match in SRT_BLOCK_RE.finditer(content):
        text = match.group("text").strip()
        if not text:
            continue
        entries.append(
            SubtitleEntry(
                start=match.group("start"),
                end=match.group("end"),
                text=text,
            )
        )
    return entries


def iter_dialogue_lines(entry: SubtitleEntry) -> Iterable[str]:
    for line in entry.normalised_text().splitlines():
        cleaned = line.strip()
        if cleaned:
            yield cleaned
