"""
Shared utility functions for the Youssef Downloader application.

Provides URL validation, human-readable formatting, filesystem helpers,
clipboard access, and FFmpeg availability checks.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from urllib.parse import parse_qs, urlsplit

import config


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_EMBED_HOSTS = {"youtube-nocookie.com", "www.youtube-nocookie.com"}


def normalize_url(url: str) -> str:
    """Normalize a scheme-less URL, without making untrusted hosts acceptable."""
    cleaned = url.strip()
    if cleaned.startswith("//"):
        return "https:" + cleaned
    if "://" not in cleaned:
        return "https://" + cleaned
    return cleaned


def validate_url(url: str) -> tuple[bool, str]:
    """Accept only video URLs on exact official YouTube hostnames."""
    if not url or not url.strip():
        return False, "Collez un lien YouTube pour continuer."
    try:
        parsed = urlsplit(normalize_url(url))
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise ValueError("Unsafe scheme or credentials")
        if parsed.port not in {None, 80, 443}:
            raise ValueError("Unexpected port")
        path = parsed.path.strip("/")
        parts = path.split("/")
        if hostname in _SHORT_HOSTS:
            video_id = parts[0]
        elif hostname in _YOUTUBE_HOSTS | _EMBED_HOSTS:
            if hostname in _YOUTUBE_HOSTS and path == "watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed", "v"}:
                video_id = parts[1]
            else:
                video_id = ""
        else:
            video_id = ""
        if _VIDEO_ID.fullmatch(video_id):
            return True, ""
    except (ValueError, TypeError):
        pass
    return False, "Lien YouTube non valide. Formats acceptés : /watch, /shorts, /live et youtu.be."


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_bytes(num_bytes: float | int | None) -> str:
    """Convert a byte count into a human-readable string (e.g. '12.4 MB')."""
    if num_bytes is None or num_bytes < 0:
        return "—"

    value = float(num_bytes)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def format_speed(speed_bytes: float | int | None) -> str:
    """Format a download speed in bytes/sec as a readable string."""
    if speed_bytes is None or speed_bytes <= 0:
        return "—"
    return f"{format_bytes(speed_bytes)}/s"


def format_duration(seconds: float | int | None) -> str:
    """
    Format a duration in seconds as HH:MM:SS or MM:SS.

    Returns '—' when the value is missing or invalid.
    """
    if seconds is None:
        return "—"

    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "—"

    if total < 0:
        return "—"

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:d}:{secs:02d}"


def format_view_count(views: int | None) -> str:
    """Format a view count with thousands separators."""
    if views is None:
        return "—"
    try:
        return f"{int(views):,}"
    except (TypeError, ValueError):
        return "—"


def format_upload_date(upload_date: str | None) -> str:
    """
    Format yt-dlp upload_date (YYYYMMDD) into a readable date string.
    """
    if not upload_date:
        return "—"

    try:
        parsed = datetime.strptime(str(upload_date), "%Y%m%d")
        return parsed.strftime("%B %d, %Y")
    except ValueError:
        return str(upload_date)


def format_eta(eta_seconds: float | int | None) -> str:
    """Format ETA seconds into a short human-readable string."""
    if eta_seconds is None or eta_seconds < 0:
        return "—"
    return format_duration(int(eta_seconds))


def format_percent(percent: float | None) -> str:
    """Format a percentage value for display."""
    if percent is None:
        return "0%"
    return f"{percent:.1f}%"


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def ensure_downloads_dir() -> Path:
    """Create the default Downloads folder and mp3/mp4 subfolders."""
    config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (config.DOWNLOADS_DIR / "mp4").mkdir(parents=True, exist_ok=True)
    (config.DOWNLOADS_DIR / "mp3").mkdir(parents=True, exist_ok=True)
    return config.DOWNLOADS_DIR


def get_format_output_dir(base_dir: Path | str | None, fmt: str) -> Path:
    """
    Resolve the output folder for a given format.

    Files are saved into ``<base>/mp4`` or ``<base>/mp3`` so downloads
    stay organized by type.
    """
    root = Path(base_dir) if base_dir else ensure_downloads_dir()
    folder = root / fmt.lower()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def browse_folder(initial_dir: Path | None = None) -> str:
    """
    Open a folder-picker dialog and return the selected path.

    Returns an empty string when the user cancels.
    """
    start = str(initial_dir or ensure_downloads_dir())
    selected = filedialog.askdirectory(
        title="Select Download Folder",
        initialdir=start,
    )
    return selected or ""


def open_folder(folder_path: str | Path) -> tuple[bool, str]:
    """
    Open a folder in the system file explorer (Windows).

    Returns:
        (success, error_message)
    """
    path = Path(folder_path)
    if not path.exists():
        return False, f"Folder does not exist:\n{path}"

    if not path.is_dir():
        return False, f"Path is not a folder:\n{path}"

    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        return True, ""
    except OSError as exc:
        return False, f"Could not open folder:\n{exc}"


def check_ffmpeg() -> tuple[bool, str]:
    """
    Verify that bundled ffmpeg executables are present.

    Returns:
        (is_available, error_message)
    """
    missing: list[str] = []
    if not config.FFMPEG_EXE.is_file():
        missing.append(config.FFMPEG_EXE.name)
    if not config.FFPROBE_EXE.is_file():
        missing.append(config.FFPROBE_EXE.name)

    if missing:
        return (
            False,
            "Composants FFmpeg introuvables.\n\n"
            f"Missing: {', '.join(missing)}\n"
            f"Expected location: {config.FFMPEG_DIR}\n\n"
            "Réinstallez la version complète de l’application (FFmpeg et ffprobe inclus).",
        )

    return True, ""


def get_ffmpeg_location() -> str:
    """Return the directory containing bundled ffmpeg binaries."""
    return str(config.FFMPEG_DIR)


# ---------------------------------------------------------------------------
# Settings (per-user, never saved in the installed program folder)
# ---------------------------------------------------------------------------

SETTINGS_FILE = config.USER_DATA_DIR / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {
            "format": data["format"] if data.get("format") in {"mp4", "mp3"} else "mp4",
            "download_dir": data["download_dir"] if isinstance(data.get("download_dir"), str) else "",
        }
    except (OSError, ValueError, TypeError, KeyError):
        return {}


def save_settings(download_dir: str, fmt: str) -> None:
    """Write preferences atomically so abrupt shutdown cannot truncate them."""
    if fmt not in {"mp4", "mp3"}:
        raise ValueError("Unsupported output format")
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = SETTINGS_FILE.with_suffix(".tmp")
    try:
        temp.write_text(json.dumps({"download_dir":download_dir, "format":fmt}, ensure_ascii=False), encoding="utf-8")
        temp.replace(SETTINGS_FILE)
    finally:
        if temp.exists():
            temp.unlink()


def open_file(file_path: str | Path) -> tuple[bool, str]:
    path = Path(file_path)
    if not path.is_file():
        return False, "The downloaded file is no longer available."
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        return True, ""
    except (OSError, subprocess.CalledProcessError) as exc:
        return False, f"Could not open the file: {exc}"


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


def paste_from_clipboard(root) -> str:
    """
    Read text from the system clipboard via a Tk root widget.

    Args:
        root: A tkinter / CustomTkinter root window instance.

    Returns:
        Clipboard text, or an empty string on failure.
    """
    try:
        return root.clipboard_get().strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Error message mapping
# ---------------------------------------------------------------------------


def classify_error(error: Exception | str) -> tuple[str, str]:
    """
    Convert yt-dlp / network exceptions into user-friendly messages.
    """
    original = str(error).strip()
    message = original.lower()

    if "private video" in message or "members-only" in message:
        return "private", "Cette vidéo est privée ou réservée aux membres."
    if "age" in message and "restrict" in message:
        return "age_restricted", "Cette vidéo nécessite une connexion et une vérification de l’âge."
    if "video unavailable" in message or "not available" in message:
        return "unavailable", "Vidéo indisponible, supprimée ou bloquée dans votre région."
    if "confirm you’re not a bot" in message or "confirm you're not a bot" in message or "bot verification" in message:
        return "bot_verification", "YouTube demande une vérification. Mettez à jour le moteur ; une connexion peut être nécessaire."
    if "sign in" in message or "login required" in message or "authentication" in message:
        return "authentication", "Cette vidéo nécessite une connexion à YouTube."
    if "po token" in message or "pot provider" in message or "po_token" in message:
        dependency = " The configured provider also needs its documented JavaScript runtime (current Node.js or Deno)." if any(x in message for x in ("node", "deno", "javascript runtime", "js runtime")) else ""
        return "po_token", "Un jeton PO est requis par YouTube. Installez un fournisseur compatible avec yt-dlp." + dependency
    if "copyright" in message:
        return "copyright", "Le téléchargement est interdit par les restrictions de droits d’auteur."
    if "ffmpeg" in message or "ffprobe" in message:
        ok, ffmpeg_msg = check_ffmpeg()
        if not ok:
            return "ffmpeg_missing", ffmpeg_msg
        return "ffmpeg", "Échec de FFmpeg pendant la fusion ou conversion. Consultez le journal."
    if "http error 403" in message or "status code 403" in message or "forbidden" in message:
        return "http_403", "YouTube a refusé la requête (HTTP 403). Mettez le moteur à jour."
    if "http error 429" in message or "status code 429" in message or "too many requests" in message:
        return "http_429", "Trop de requêtes (HTTP 429). Réessayez plus tard."
    if "fragment" in message and any(x in message for x in ("failed", "unavailable", "error")):
        return "fragment", "Un fragment du fichier a échoué. Réessayez pour reprendre le téléchargement."
    if any(x in message for x in ("url has expired", "expired url", "signature extraction", "nsig extraction", "extractor error")):
        return "extraction", "Le lien du média a expiré. Mettez le moteur à jour et réessayez."
    if any(
        token in message
        for token in (
            "network",
            "connection",
            "timed out",
            "timeout",
            "urlopen error",
            "getaddrinfo failed",
            "no route to host",
            "name or service not known",
        )
    ):
        return "network", (
            "Network error — please check your internet connection "
            "and try again."
        )
    if "http error 404" in message or "404" in message:
        return "not_found", "Vidéo introuvable. Vérifiez le lien."
    if "invalid" in message and "url" in message:
        return "invalid_url", "Le lien semble invalide."

    # Fall back to the original message, trimmed for readability
    if len(original) > 300:
        original = original[:297] + "..."
    return "unknown", original or "Une erreur inattendue s’est produite."


def friendly_error_message(error: Exception | str) -> str:
    """Return the short user-facing half of :func:`classify_error`."""
    return classify_error(error)[1]
