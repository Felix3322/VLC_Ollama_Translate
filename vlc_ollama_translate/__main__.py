"""Command line entry point for VLC Ollama Translate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .api_client import APIError
from .config import PluginConfig, load_config, save_config
from .languages import LANGUAGES
from .model_limits import get_model_max_tokens
from .subtitle import parse_srt
from .translator import SubtitleTranslator


def _validate_language(code: str) -> str:
    if code not in LANGUAGES:
        raise SystemExit(f"Unsupported language code: {code}")
    return code


def cmd_configure(args: argparse.Namespace) -> None:
    cfg = load_config()
    if args.login_string:
        cfg.update_from_login_string(args.login_string)
    if args.api_key is not None:
        cfg.api_key = args.api_key
    if args.model is not None:
        cfg.selected_model = args.model
    if args.api_url is not None:
        cfg.api_url = args.api_url
    if args.delay_ms is not None:
        cfg.delay_ms = args.delay_ms
    if args.retry_mode is not None:
        cfg.retry_mode = args.retry_mode
    if args.context_budget is not None:
        cfg.context_token_budget = args.context_budget
    if args.truncation_mode is not None:
        cfg.context_truncation_mode = args.truncation_mode
    if args.cache_mode is not None:
        cfg.context_cache_mode = args.cache_mode
    if args.source_language is not None:
        cfg.source_language = args.source_language
    if args.target_language is not None:
        cfg.target_language = args.target_language
    cfg.save()
    print("Configuration updated", file=sys.stderr)


def cmd_show_config(args: argparse.Namespace) -> None:
    cfg = load_config()
    data = cfg.to_dict()
    for key in sorted(data):
        value = data[key]
        if isinstance(value, dict):
            import json

            print(f"{key}={json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key}={value}")


def _format_block(index: int, start: str, end: str, lines: List[str]) -> str:
    block_lines = [str(index), f"{start} --> {end}"] + lines + [""]
    return "\n".join(block_lines)


def cmd_translate(args: argparse.Namespace) -> None:
    cfg = load_config()
    if args.api_key:
        cfg.api_key = args.api_key
    if not cfg.api_key and args.require_key:
        raise SystemExit("API key not configured. Use the configure command or pass --api-key.")
    if args.source_language:
        cfg.source_language = _validate_language(args.source_language)
    if args.target_language:
        cfg.target_language = _validate_language(args.target_language)
    cfg.normalise_languages()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise SystemExit(f"Input subtitle file does not exist: {input_path}")

    content = input_path.read_text(encoding="utf-8")
    entries = parse_srt(content)
    if not entries:
        raise SystemExit("No subtitle entries found in the input file")

    max_tokens = get_model_max_tokens(cfg)
    translator = SubtitleTranslator(cfg, max_tokens)
    translated_blocks: List[str] = []
    index = 1
    for entry in entries:
        text = entry.normalised_text()
        if not text:
            continue
        try:
            result = translator.translate(text)
        except APIError as exc:
            raise SystemExit(f"Translation failed: {exc}")
        if args.include_original:
            original_lines = [line for line in entry.normalised_text().splitlines() if line.strip()]
            lines = [result.translated]
            lines.extend(original_lines)
        else:
            lines = [result.translated]
        translated_blocks.append(_format_block(index, entry.start, entry.end, lines))
        index += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(translated_blocks), encoding="utf-8")
    print(f"Translated subtitles written to {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VLC Ollama Translate utility")
    subparsers = parser.add_subparsers(dest="command")

    configure = subparsers.add_parser("configure", help="Update stored configuration")
    configure.add_argument("--login-string", help="PotPlayer style configuration string", default="")
    configure.add_argument("--api-key")
    configure.add_argument("--model")
    configure.add_argument("--api-url")
    configure.add_argument("--delay-ms", type=int)
    configure.add_argument("--retry-mode", type=int)
    configure.add_argument("--context-budget", type=int)
    configure.add_argument("--truncation-mode", choices=["drop_oldest", "smart_trim"])
    configure.add_argument("--cache-mode", choices=["auto", "off"])
    configure.add_argument("--source-language")
    configure.add_argument("--target-language")
    configure.set_defaults(func=cmd_configure)

    show_cfg = subparsers.add_parser("show-config", help="Print the current configuration")
    show_cfg.set_defaults(func=cmd_show_config)

    translate = subparsers.add_parser("translate", help="Translate a subtitle file")
    translate.add_argument("--input", required=True, help="Path to the subtitle file (SRT)")
    translate.add_argument("--output", required=True, help="Output path for the translated SRT")
    translate.add_argument("--include-original", action="store_true", help="Include original text above the translation")
    translate.add_argument("--api-key", help="Override API key for this run")
    translate.add_argument("--source-language", help="Override the configured source language")
    translate.add_argument("--target-language", help="Override the configured target language")
    translate.add_argument("--require-key", action="store_true", help="Fail if no API key is configured")
    translate.set_defaults(func=cmd_translate)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
