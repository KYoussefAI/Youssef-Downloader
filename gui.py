"""
CustomTkinter graphical user interface for Youssef Downloader.

All network and download work runs on background threads; UI updates are
marshalled back to the main thread via ``after()``.
"""

from __future__ import annotations

import io
import threading
import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk
import requests
from PIL import Image

import config
import utils
from app_logging import get_logger
from downloader import DownloadFormat, DownloadStatus, VideoInfo, YouTubeDownloader


class YouTubeDownloaderApp(ctk.CTk):
    """
    Main application window.

    Manages layout, user interaction, and coordinates with
    :class:`YouTubeDownloader` on background threads.
    """

    def __init__(self) -> None:
        super().__init__()

        # Core services (no globals — owned by the window instance)
        self._downloader = YouTubeDownloader()
        self._logger = get_logger()
        self._analyze_thread: threading.Thread | None = None
        self._download_thread: threading.Thread | None = None
        self._analyzed: bool = False
        self._busy: bool = False
        self._downloading: bool = False
        self._thumbnail_image: ctk.CTkImage | None = None

        self._configure_window()
        self._build_layout()
        self._set_default_state()
        self.after(0, self._start_downloader_version_check)

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _configure_window(self) -> None:
        """Apply theme, title, geometry, and icon settings."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Explicitly set AppUserModelID on Windows for proper taskbar icon integration
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "YoussefDownloader.App.1.0"
                )
            except Exception:
                pass

        self.title(config.APP_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(config.MIN_WINDOW_WIDTH, config.MIN_WINDOW_HEIGHT)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - config.WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - config.WINDOW_HEIGHT) // 2
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}+{x}+{y}")

        if config.ICON_PATH.is_file():
            try:
                self.iconbitmap(str(config.ICON_PATH))
            except Exception:
                pass  # Icon is optional — never crash on bad .ico

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Assemble all UI sections top-to-bottom."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        container.grid_columnconfigure(0, weight=1)

        row = 0
        row = self._build_header(container, row)
        row = self._build_url_section(container, row)
        row = self._build_video_info_section(container, row)
        row = self._build_download_options(container, row)
        row = self._build_location_section(container, row)
        row = self._build_progress_section(container, row)
        row = self._build_download_button(container, row)

    def _build_header(self, parent: ctk.CTkFrame, row: int) -> int:
        """Logo and application title."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)

        if config.LOGO_PATH.is_file():
            try:
                logo_img = Image.open(config.LOGO_PATH)
                self._logo_ctk = ctk.CTkImage(
                    light_image=logo_img,
                    dark_image=logo_img,
                    size=(48, 48),
                )
                ctk.CTkLabel(header, image=self._logo_ctk, text="").grid(
                    row=0, column=0, padx=(0, 12)
                )
            except Exception:
                pass

        ctk.CTkLabel(
            header,
            text=config.APP_TITLE,
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        tools = ctk.CTkFrame(header, fg_color="transparent")
        tools.grid(row=0, column=2, sticky="e")
        self.downloader_version_label = ctk.CTkLabel(
            tools, text="yt-dlp: detecting...", text_color="gray65"
        )
        self.downloader_version_label.grid(row=0, column=0, padx=(0, 8))
        self.update_downloader_btn = ctk.CTkButton(
            tools, text="Update downloader", width=130, fg_color="#555555",
            hover_color="#666666", command=self._on_update_downloader
        )
        self.update_downloader_btn.grid(row=0, column=1)

        return row + 1

    def _build_url_section(self, parent: ctk.CTkFrame, row: int) -> int:
        """URL input row with Paste, Analyze, and Clear buttons."""
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text="YouTube URL",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 4))

        self.url_entry = ctk.CTkEntry(
            section,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=38,
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=(12, 8), pady=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self._on_analyze())

        btn_frame = ctk.CTkFrame(section, fg_color="transparent")
        btn_frame.grid(row=1, column=1, sticky="e", padx=(0, 12), pady=(0, 10))

        self.paste_btn = ctk.CTkButton(
            btn_frame, text="Paste", width=80, command=self._on_paste
        )
        self.paste_btn.grid(row=0, column=0, padx=4)

        self.analyze_btn = ctk.CTkButton(
            btn_frame,
            text="Analyze",
            width=90,
            fg_color="#1f6aa5",
            command=self._on_analyze,
        )
        self.analyze_btn.grid(row=0, column=1, padx=4)

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear",
            width=80,
            fg_color="#555555",
            hover_color="#666666",
            command=self._on_clear,
        )
        self.clear_btn.grid(row=0, column=2, padx=4)

        return row + 1

    def _build_video_info_section(self, parent: ctk.CTkFrame, row: int) -> int:
        """Thumbnail and metadata display panel."""
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            section,
            text="Video Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 8))

        # Thumbnail placeholder
        self.thumbnail_label = ctk.CTkLabel(
            section,
            text="No video analyzed",
            width=config.THUMBNAIL_WIDTH,
            height=config.THUMBNAIL_HEIGHT,
            fg_color=("#d9d9d9", "#2b2b2b"),
            corner_radius=8,
        )
        self.thumbnail_label.grid(
            row=1, column=0, rowspan=6, padx=12, pady=(0, 12), sticky="nw"
        )

        # Metadata labels (label : value pairs)
        meta_frame = ctk.CTkFrame(section, fg_color="transparent")
        meta_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 12), pady=(0, 12))
        meta_frame.grid_columnconfigure(1, weight=1)

        fields = [
            ("title", "Title"),
            ("uploader", "Uploader"),
            ("duration", "Duration"),
            ("resolution", "Resolution"),
            ("views", "Views"),
            ("upload_date", "Upload Date"),
        ]
        self._meta_labels: dict[str, ctk.CTkLabel] = {}

        for idx, (key, label_text) in enumerate(fields):
            ctk.CTkLabel(
                meta_frame,
                text=f"{label_text}:",
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            ).grid(row=idx, column=0, sticky="nw", pady=3, padx=(0, 8))

            value_label = ctk.CTkLabel(
                meta_frame,
                text="—",
                anchor="w",
                wraplength=420,
                justify="left",
            )
            value_label.grid(row=idx, column=1, sticky="ew", pady=3)
            self._meta_labels[key] = value_label

        return row + 1

    def _build_download_options(self, parent: ctk.CTkFrame, row: int) -> int:
        """MP4 / MP3 radio buttons."""
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            section,
            text="Download Options",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.format_var = tk.StringVar(value=DownloadFormat.MP4.value)

        options_frame = ctk.CTkFrame(section, fg_color="transparent")
        options_frame.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        ctk.CTkRadioButton(
            options_frame,
            text="MP4 Video (highest quality)",
            variable=self.format_var,
            value=DownloadFormat.MP4.value,
        ).grid(row=0, column=0, padx=(0, 24), pady=4)

        ctk.CTkRadioButton(
            options_frame,
            text="MP3 Audio (320 kbps)",
            variable=self.format_var,
            value=DownloadFormat.MP3.value,
        ).grid(row=0, column=1, pady=4)

        return row + 1

    def _build_location_section(self, parent: ctk.CTkFrame, row: int) -> int:
        """Download folder path with Browse and Open Folder."""
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text="Download Location",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 4))

        default_dir = str(utils.ensure_downloads_dir())
        self.location_entry = ctk.CTkEntry(section, height=38)
        self.location_entry.insert(0, default_dir)
        self.location_entry.grid(row=1, column=0, sticky="ew", padx=(12, 8), pady=(0, 10))

        btn_frame = ctk.CTkFrame(section, fg_color="transparent")
        btn_frame.grid(row=1, column=1, sticky="e", padx=(0, 12), pady=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Browse", width=90, command=self._on_browse
        ).grid(row=0, column=0, padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Open Folder",
            width=100,
            fg_color="#555555",
            hover_color="#666666",
            command=self._on_open_folder,
        ).grid(row=0, column=1, padx=4)

        return row + 1

    def _build_progress_section(self, parent: ctk.CTkFrame, row: int) -> int:
        """Progress bar, stats, and status label."""
        section = ctk.CTkFrame(parent)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text="Progress",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(section, height=16)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        stats_frame = ctk.CTkFrame(section, fg_color="transparent")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=12)
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.percent_label = ctk.CTkLabel(stats_frame, text="0%", anchor="w")
        self.percent_label.grid(row=0, column=0, sticky="w")

        self.size_label = ctk.CTkLabel(stats_frame, text="0 B / —", anchor="center")
        self.size_label.grid(row=0, column=1)

        self.speed_label = ctk.CTkLabel(stats_frame, text="Speed: —", anchor="center")
        self.speed_label.grid(row=0, column=2)

        self.eta_label = ctk.CTkLabel(
            section, text="ETA: —", anchor="w", text_color="gray70"
        )
        self.eta_label.grid(row=3, column=0, sticky="w", padx=12, pady=(2, 0))

        self.status_label = ctk.CTkLabel(
            section,
            text="Ready",
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        self.status_label.grid(row=4, column=0, sticky="w", padx=12, pady=(4, 12))

        return row + 1

    def _build_download_button(self, parent: ctk.CTkFrame, row: int) -> int:
        """Primary download action button."""
        self.download_btn = ctk.CTkButton(
            parent,
            text="Download",
            height=48,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#2fa572",
            hover_color="#248f61",
            state="disabled",
            command=self._on_download,
        )
        self.download_btn.grid(row=row, column=0, sticky="ew", pady=(4, 8))
        return row + 1

    # ------------------------------------------------------------------
    # Default / reset state
    # ------------------------------------------------------------------

    def _set_default_state(self) -> None:
        """Initialize UI to idle-ready state."""
        self._analyzed = False
        self._reset_progress()
        self._set_status("Ready — paste a URL and click Analyze.")
        self._enable_download(False)

    def _reset_progress(self) -> None:
        """Clear all progress indicators."""
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        self.size_label.configure(text="0 B / —")
        self.speed_label.configure(text="Speed: —")
        self.eta_label.configure(text="ETA: —")

    def _reset_video_info(self) -> None:
        """Clear the video information panel."""
        for label in self._meta_labels.values():
            label.configure(text="—")

        self._thumbnail_image = None
        self.thumbnail_label.configure(
            image=None,
            text="No video analyzed",
        )

    # ------------------------------------------------------------------
    # Thread-safe UI helpers
    # ------------------------------------------------------------------

    def _run_on_main(self, func, *args, **kwargs) -> None:
        """Schedule a callable on the Tk main loop."""
        self.after(0, lambda: func(*args, **kwargs))

    def _set_status(self, message: str, *, is_error: bool = False) -> None:
        """Update the status label."""
        color = "#ff6b6b" if is_error else ("gray70" if message == "Ready" else "white")
        self.status_label.configure(text=message, text_color=color)

    def _set_busy(self, busy: bool, *, for_download: bool = False) -> None:
        """Disable interactive controls while a background task runs."""
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.analyze_btn.configure(state=state)
        self.paste_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.url_entry.configure(state=state)

        if for_download and busy:
            self._set_download_button_cancel()
        elif not busy:
            self._set_download_button_idle(self._analyzed)
        elif busy:
            self._set_download_button_idle(False)

    def _set_download_button_idle(self, enabled: bool) -> None:
        """Show the green Download button (idle state)."""
        self._downloading = False
        self.download_btn.configure(
            text="Download",
            fg_color="#2fa572",
            hover_color="#248f61",
            state="normal" if enabled else "disabled",
            command=self._on_download,
        )

    def _set_download_button_cancel(self) -> None:
        """Switch the main button to red Cancel while downloading."""
        self._downloading = True
        self.download_btn.configure(
            text="Cancel",
            fg_color="#c0392b",
            hover_color="#a93226",
            state="normal",
            command=self._on_cancel_download,
        )

    def _enable_download(self, enabled: bool) -> None:
        """Enable or disable the main Download button."""
        if not self._downloading:
            self._set_download_button_idle(enabled)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_paste(self) -> None:
        """Paste clipboard contents into the URL field."""
        text = utils.paste_from_clipboard(self)
        if text:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, text)

    def _on_clear(self) -> None:
        """Reset URL field, metadata, and progress."""
        if self._busy:
            return

        self.url_entry.delete(0, tk.END)
        self._analyzed = False
        self._reset_video_info()
        self._reset_progress()
        self._set_status("Ready — paste a URL and click Analyze.")
        self._enable_download(False)

    def _on_browse(self) -> None:
        """Open folder picker for download location."""
        current = self.location_entry.get().strip()
        initial = Path(current) if current else utils.ensure_downloads_dir()
        selected = utils.browse_folder(initial)
        if selected:
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, selected)

    def _on_open_folder(self) -> None:
        """Open the mp3/mp4 subfolder matching the selected format."""
        base = self.location_entry.get().strip() or str(utils.ensure_downloads_dir())
        fmt = self.format_var.get()
        folder = utils.get_format_output_dir(base, fmt)
        ok, msg = utils.open_folder(folder)
        if not ok:
            self._set_status(msg, is_error=True)

    def _on_analyze(self) -> None:
        """Validate URL and fetch metadata on a background thread."""
        if self._busy:
            return

        url = self.url_entry.get().strip()
        is_valid, error_msg = utils.validate_url(url)
        if not is_valid:
            self._set_status(error_msg, is_error=True)
            return

        self._analyzed = False
        self._enable_download(False)
        self._reset_video_info()
        self._reset_progress()
        self._set_busy(True)
        self._set_status("Analyzing video...")

        self._analyze_thread = threading.Thread(
            target=self._analyze_worker,
            args=(utils.normalize_url(url),),
            daemon=True,
        )
        self._analyze_thread.start()

    def _on_download(self) -> None:
        """Start download on a background thread."""
        if self._busy or not self._analyzed:
            return

        url = self.url_entry.get().strip()
        is_valid, error_msg = utils.validate_url(url)
        if not is_valid:
            self._set_status(error_msg, is_error=True)
            return

        output_dir = self.location_entry.get().strip()
        if not output_dir:
            self._set_status("Please select a download folder.", is_error=True)
            return

        fmt = DownloadFormat(self.format_var.get())
        format_dir = utils.get_format_output_dir(output_dir, fmt.value)

        self._set_busy(True, for_download=True)
        self._reset_progress()
        self._set_status("Starting download...")

        self._download_thread = threading.Thread(
            target=self._download_worker,
            args=(utils.normalize_url(url), format_dir, fmt),
            daemon=True,
        )
        self._download_thread.start()

    def _on_cancel_download(self) -> None:
        """Request cancellation of the active download."""
        if not self._downloading:
            return

        self._downloader.request_cancel()
        self._set_status("Cancelling download...")
        self.download_btn.configure(state="disabled")

    def _on_update_downloader(self) -> None:
        """Run the official yt-dlp updater without blocking the GUI."""
        if self._busy:
            return
        self._set_busy(True)
        self.update_downloader_btn.configure(state="disabled")
        self._set_status("Updating downloader...")
        threading.Thread(target=self._update_downloader_worker, daemon=True).start()

    def _start_downloader_version_check(self) -> None:
        threading.Thread(target=self._downloader_version_worker, daemon=True).start()

    def _downloader_version_worker(self) -> None:
        self._logger.info("version worker start thread=%s", threading.current_thread().name)
        version = self._downloader.ytdlp_version
        self._logger.info("version worker end version=%s", version)
        self._run_on_main(self.downloader_version_label.configure, text=f"yt-dlp {version}")

    def _update_downloader_worker(self) -> None:
        self._logger.info("updater worker start thread=%s", threading.current_thread().name)
        ok, message = self._downloader.update_downloader()
        version = self._downloader.ytdlp_version
        self._logger.info("updater worker end ok=%s version=%s", ok, version)
        self._run_on_main(self._on_update_downloader_done, ok, message, version)

    def _on_update_downloader_done(self, ok: bool, message: str, version: str) -> None:
        self._set_busy(False)
        self.update_downloader_btn.configure(state="normal")
        self.downloader_version_label.configure(text=f"yt-dlp {version}")
        self._set_status(message, is_error=not ok)

    # ------------------------------------------------------------------
    # Background workers
    # ------------------------------------------------------------------

    def _analyze_worker(self, url: str) -> None:
        """Fetch metadata via yt-dlp (runs off the main thread)."""
        self._logger.info("analyze worker start thread=%s", threading.current_thread().name)
        try:
            info = self._downloader.extract_info(url)
            self._run_on_main(self._on_analyze_success, info)
        except Exception as exc:
            self._run_on_main(self._on_analyze_error, str(exc))
        finally:
            self._logger.info("analyze worker end")

    def _download_worker(
        self, url: str, output_dir: Path, fmt: DownloadFormat
    ) -> None:
        """Download / convert via yt-dlp (runs off the main thread)."""
        self._logger.info("download worker start thread=%s", threading.current_thread().name)
        try:
            output_path = self._downloader.download(
                url,
                output_dir,
                fmt,
                progress_callback=lambda data: self._run_on_main(
                    self._on_download_progress, data
                ),
            )
            self._run_on_main(self._on_download_success, output_path)
        except Exception as exc:
            self._run_on_main(self._on_download_error, str(exc))
        finally:
            self._logger.info("download worker end")

    # ------------------------------------------------------------------
    # Worker callbacks (main thread)
    # ------------------------------------------------------------------

    def _on_analyze_success(self, info: VideoInfo) -> None:
        """Populate UI with extracted video metadata."""
        self._analyzed = True
        self._set_busy(False)
        self._enable_download(True)

        self._meta_labels["title"].configure(text=info.title)
        self._meta_labels["uploader"].configure(text=info.uploader)
        self._meta_labels["duration"].configure(
            text=utils.format_duration(info.duration)
        )
        self._meta_labels["resolution"].configure(text=info.resolution)
        self._meta_labels["views"].configure(
            text=utils.format_view_count(info.view_count)
        )
        self._meta_labels["upload_date"].configure(
            text=utils.format_upload_date(info.upload_date)
        )

        self._set_status("Analysis complete — ready to download.")
        self._load_thumbnail(info.thumbnail_url)

    def _on_analyze_error(self, message: str) -> None:
        """Handle metadata extraction failure."""
        self._analyzed = False
        self._set_busy(False)
        self._enable_download(False)
        self._set_status(message, is_error=True)

    def _on_download_progress(self, data: dict[str, Any]) -> None:
        """Update progress bar and stats from yt-dlp hooks."""
        status = data.get("status", "")
        percent = float(data.get("percent", 0.0))
        downloaded = data.get("downloaded_bytes")
        total = data.get("total_bytes")
        speed = data.get("speed")
        eta = data.get("eta")
        message = data.get("message", "")

        self.progress_bar.set(max(0.0, min(1.0, percent / 100.0)))
        self.percent_label.configure(text=utils.format_percent(percent))
        self.size_label.configure(
            text=f"{utils.format_bytes(downloaded)} / {utils.format_bytes(total)}"
        )
        self.speed_label.configure(text=f"Speed: {utils.format_speed(speed)}")
        self.eta_label.configure(text=f"ETA: {utils.format_eta(eta)}")

        if status == DownloadStatus.DOWNLOADING.value:
            self._set_status("Downloading...")
        elif status == DownloadStatus.CONVERTING.value:
            self._set_status("Converting...")
        elif message:
            self._set_status(message)

    def _on_download_success(self, output_path: str) -> None:
        """Handle successful download completion."""
        self._set_busy(False)
        self.progress_bar.set(1.0)
        self.percent_label.configure(text="100%")
        self._set_status(f"Finished — saved to:\n{output_path}")

    def _on_download_error(self, message: str) -> None:
        """Handle download failure or cancellation."""
        self._set_busy(False)
        if "cancel" in message.lower():
            self._reset_progress()
            self._set_status("Download cancelled.")
        else:
            self._set_status(message, is_error=True)

    # ------------------------------------------------------------------
    # Thumbnail loading
    # ------------------------------------------------------------------

    def _load_thumbnail(self, url: str | None) -> None:
        """Fetch and display the video thumbnail asynchronously."""
        if not url:
            return

        def worker(thumbnail_url: str) -> None:
            try:
                response = requests.get(thumbnail_url, timeout=15)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
                self._run_on_main(self._display_thumbnail, image)
            except Exception:
                self._run_on_main(
                    self.thumbnail_label.configure,
                    text="Thumbnail unavailable",
                )

        threading.Thread(target=worker, args=(url,), daemon=True).start()

    def _display_thumbnail(self, image: Image.Image) -> None:
        """Render a PIL image in the thumbnail label."""
        try:
            image = image.convert("RGB")
            self._thumbnail_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(config.THUMBNAIL_WIDTH, config.THUMBNAIL_HEIGHT),
            )
            self.thumbnail_label.configure(image=self._thumbnail_image, text="")
        except Exception:
            self.thumbnail_label.configure(text="Thumbnail unavailable", image=None)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_closing(self) -> None:
        """Clean shutdown — request cancellation of active downloads."""
        self._downloader.request_cancel()
        self.destroy()


def run_app() -> None:
    """Create the main window and start the Tk event loop."""
    app = YouTubeDownloaderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
