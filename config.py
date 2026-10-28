"""
Application configuration and path resolution.

Handles frozen (PyInstaller) vs script execution modes and exposes
all portable, relative paths used throughout the application.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path


def _resolve_resource_dir() -> Path:
    """
    Resolve the directory containing application bundled resources.

    When compiled with PyInstaller (--onefile), resources are extracted to sys._MEIPASS.
    When run as a script, resources live in the project directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent


def _resolve_exe_dir() -> Path:
    """
    Resolve the directory where the executable or main script resides.

    User outputs (like Downloads/) are placed relative to this directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_downloads_dir() -> Path:
    """
    Resolve default download directory on the user's Desktop.

    Supports standard Windows Desktop and OneDrive redirected Desktop folders.
    """
    home = Path.home()
    onedrive_desktop = home / "OneDrive" / "Desktop"
    desktop = onedrive_desktop if onedrive_desktop.is_dir() else (home / "Desktop")
    return desktop / "ISSA Downloader"


RESOURCE_DIR: Path = _resolve_resource_dir()
EXE_DIR: Path = _resolve_exe_dir()
BASE_DIR: Path = RESOURCE_DIR  # Maintained for backward compatibility

ASSETS_DIR: Path = RESOURCE_DIR / "assets"
DOWNLOADS_DIR: Path = _resolve_downloads_dir()


def _resolve_ffmpeg_dir() -> Path:
    """
    Locate bundled FFmpeg binaries.

    Checks candidates inside RESOURCE_DIR (sys._MEIPASS when frozen)
    and EXE_DIR. Supports flat layouts, ffmpeg/bin layout, and root layout.
    """
    candidates = (
        RESOURCE_DIR / "ffmpeg" / "bin",
        RESOURCE_DIR / "ffmpeg",
        RESOURCE_DIR,
        EXE_DIR / "ffmpeg" / "bin",
        EXE_DIR / "ffmpeg",
    )
    for directory in candidates:
        if (directory / "ffmpeg.exe").is_file() and (directory / "ffprobe.exe").is_file():
            return directory
    # Default expected location fallback
    return RESOURCE_DIR / "ffmpeg" / "bin"


FFMPEG_DIR: Path = _resolve_ffmpeg_dir()

LOGO_PATH: Path = ASSETS_DIR / "issa-logo.png"
ICON_PATH: Path = ASSETS_DIR / "issa.ico"
FFMPEG_EXE: Path = FFMPEG_DIR / "ffmpeg.exe"
FFPROBE_EXE: Path = FFMPEG_DIR / "ffprobe.exe"


def _resolve_deno_exe() -> Path:
    candidates = (
        RESOURCE_DIR / "runtime" / "deno.exe",
        EXE_DIR / "runtime" / "deno.exe",
        Path(__file__).resolve().parent / "runtime" / "deno.exe",
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


DENO_EXE: Path = _resolve_deno_exe()

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------

APP_TITLE: str = "ISSA Downloader"
APP_VERSION: str = "2.0.0"
APP_PUBLISHER: str = "ISSA"
APP_EXECUTABLE: str = "ISSA.exe"
APP_DESCRIPTION: str = "ISSA — video and audio downloader"
APP_COPYRIGHT: str = "Copyright (c) 2026 ISSA"


def _resolve_user_data_dir() -> Path:
    """Return a stable per-user writable directory for logs and runtime updates."""
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / APP_TITLE


USER_DATA_DIR: Path = _resolve_user_data_dir()
LOG_DIR: Path = USER_DATA_DIR / "logs"
DOWNLOADER_RUNTIME_DIR: Path = USER_DATA_DIR / "runtime"
YTDLP_EXE_NAME: str = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
YTDLP_UPDATE_CHECK_FILE: Path = DOWNLOADER_RUNTIME_DIR / "last_update_check.json"
YTDLP_UPDATE_INTERVAL_HOURS: int = 72

# ---------------------------------------------------------------------------
# Window / UI defaults
# ---------------------------------------------------------------------------

WINDOW_WIDTH: int = 900
WINDOW_HEIGHT: int = 650
MIN_WINDOW_WIDTH: int = 800
MIN_WINDOW_HEIGHT: int = 600

# Thumbnail display size in the video-info panel
THUMBNAIL_WIDTH: int = 320
THUMBNAIL_HEIGHT: int = 180

# ---------------------------------------------------------------------------
# Download defaults
# ---------------------------------------------------------------------------

DEFAULT_DOWNLOAD_FORMAT: str = "mp4"  # "mp4" or "mp3"
MP3_BITRATE: str = "320"  # Preferred MP3 quality in kbps

# yt-dlp format selectors
MP4_FORMAT: str = (
    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
    "bestvideo+bestaudio/"
    "best[ext=mp4]/best"
)
MP3_FORMAT: str = "bestaudio/best"

# ---------------------------------------------------------------------------
# Supported YouTube URL patterns (validated in utils.validate_url)
# ---------------------------------------------------------------------------

YOUTUBE_URL_PATTERNS: tuple[str, ...] = (
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+",
    r"(?:https?://)?youtu\.be/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/live/[\w-]+",
)
