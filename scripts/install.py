#!/usr/bin/env python3
"""Automate installation of VLC Ollama Translate."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def default_extensions_dir() -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return appdata / "vlc" / "lua" / "extensions"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "org.videolan.vlc" / "lua" / "extensions"
    return home / ".local" / "share" / "vlc" / "lua" / "extensions"


def run_pip_install(repo_root: Path, *, user: bool) -> None:
    cmd = [sys.executable, "-m", "pip", "install"]
    if user:
        cmd.append("--user")
    cmd.append(str(repo_root))
    subprocess.run(cmd, check=True)


def copy_extension(repo_root: Path, destination: Path) -> Path:
    source = repo_root / "lua" / "extensions" / "chatgpt_translate.lua"
    if not source.exists():
        raise FileNotFoundError(f"Extension script not found: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    shutil.copy2(source, target)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the VLC Ollama Translate plugin")
    parser.add_argument(
        "--extensions-dir",
        type=Path,
        help="Override the VLC extensions directory",
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip installing the Python package with pip",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Install the Python package in the user site-packages (pip --user)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    try:
        if not args.skip_pip:
            print("Installing Python package via pip...")
            run_pip_install(repo_root, user=args.user)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to install Python package: {exc}", file=sys.stderr)
        sys.exit(1)

    extensions_dir = args.extensions_dir or default_extensions_dir()
    target = copy_extension(repo_root, extensions_dir)
    print(f"Extension copied to: {target}")
    print("Installation complete.")


if __name__ == "__main__":
    main()
