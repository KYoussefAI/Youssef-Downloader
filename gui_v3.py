"""ISSA Downloader v3: compact, French-first desktop interface."""
from __future__ import annotations

import io
import queue
import threading
import tkinter as tk
from pathlib import Path

from progress_tracking import monotonic_download_percent
import customtkinter as ctk
import requests
from PIL import Image

import config
import utils
from app_logging import get_logger
from downloader import DownloadFormat, VideoInfo, YouTubeDownloader

BG = "#0c111d"
PANEL = "#151d2c"
PANEL_ALT = "#192336"
BORDER = "#2d3b54"
WHITE = "#f6f7ff"
MUTED = "#a2aec7"
ACCENT = "#7445ed"
ACCENT_HOVER = "#8a62fa"
BLUE = "#546ff0"
GREEN = "#35c89e"
RED = "#e15e75"
FONT = "Segoe UI"


class ISSADownloaderApp(ctk.CTk):
    """One screen: paste, analyze, choose MP4/MP3, download, open, next."""

    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.log = get_logger()
        self.engine = YouTubeDownloader()
        self._queue: queue.Queue = queue.Queue()
        self._closing = False
        self._mode = "idle"
        self._sequence = 0
        self._analyzed_url = ""
        self._info: VideoInfo | None = None
        self._output: Path | None = None
        self._thumb_ref = None
        self.format_var = tk.StringVar(value="mp4")
        self.quality_var = tk.StringVar(value="Meilleure")
        self.title(config.APP_TITLE)
        self.geometry("1100x758")
        self.minsize(925, 695)
        self.configure(fg_color=BG)
        self._set_windows_icon()
        self._build()
        self._reset_progress()
        self._set_status("Prêt — collez un lien puis cliquez sur Analyser.")
        self._update_controls()
        self.after(60, self._pump)

    def _set_windows_icon(self) -> None:
        if config.ICON_PATH.is_file():
            try:
                self.iconbitmap(str(config.ICON_PATH))
            except (OSError, tk.TclError):
                pass
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ISSA.Downloader.3")
            except (AttributeError, OSError):
                pass

    @staticmethod
    def _label(parent, text, size=13, color=WHITE, bold=False, **kwargs):
        return ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(family=FONT, size=size,
            weight="bold" if bold else "normal"), text_color=color, **kwargs
        )

    @staticmethod
    def _panel(parent):
        return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=13,
                            border_width=1, border_color=BORDER)

    def _button(self, parent, text, command, primary=False):
        return ctk.CTkButton(
            parent, text=text, command=command, height=47, corner_radius=10,
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            fg_color=ACCENT if primary else PANEL_ALT,
            hover_color=ACCENT_HOVER if primary else "#28354f",
            border_width=0 if primary else 1, border_color="#51617e",
            text_color=WHITE
        )

    def _build(self) -> None:
        # All controls fit in the window: no scrolling or empty hero margins.
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=23, pady=(14, 16))

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", pady=(0, 13))
        try:
            original = Image.open(config.LOGO_PATH).convert("RGBA")
            self._brand_image = ctk.CTkImage(light_image=original,
                                              dark_image=original, size=(43, 43))
            ctk.CTkLabel(header, text="", image=self._brand_image,
                         width=48).pack(side="left", padx=(0, 9))
        except (OSError, ValueError):
            self._label(header, "▶", 27, ACCENT, True).pack(side="left", padx=(0, 12))
        self._label(header, "ISSA Downloader", 26, WHITE, True).pack(side="left")
        self._label(header, "Vidéo MP4  •  Audio MP3", 12, MUTED).pack(side="right")

        url_panel = self._panel(root)
        url_panel.pack(fill="x")
        self._label(url_panel, "LIEN DE LA VIDÉO", 12, MUTED, True).pack(
            anchor="w", padx=16, pady=(10, 4))
        url_row = ctk.CTkFrame(url_panel, fg_color="transparent")
        url_row.pack(fill="x", padx=15, pady=(0, 12))
        self.url_entry = ctk.CTkEntry(
            url_row, height=44, corner_radius=9, fg_color="#101827",
            border_color="#465779", text_color=WHITE, font=ctk.CTkFont(family=FONT,size=14),
            placeholder_text="https://www.youtube.com/watch?v=..."
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self._analyze())
        self.url_entry.bind("<KeyRelease>", lambda _e: self._on_url_change())
        self.paste_btn = ctk.CTkButton(
            url_row, text="Coller", width=113, height=44, command=self._paste,
            corner_radius=9, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(family=FONT,size=15,weight="bold")
        )
        self.paste_btn.pack(side="right")

        action_row = ctk.CTkFrame(root, fg_color="transparent")
        action_row.pack(fill="x", pady=(10, 12))
        self.analyze_btn = self._button(action_row, "⌕  Analyser", self._analyze)
        self.analyze_btn.pack(side="left", fill="x", expand=True, padx=(0, 9))
        self.download_btn = self._button(action_row, "↓  Télécharger",
                                          self._download, primary=True)
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(9, 0))

        info_panel = self._panel(root)
        info_panel.pack(fill="x", pady=(0, 12))
        self.thumb = self._label(info_panel, "Aperçu de la vidéo", 13, MUTED,
                                 width=235, height=130,
                                 fg_color="#0f1726", corner_radius=9)
        self.thumb.pack(side="left", padx=13, pady=12)
        info_right = ctk.CTkFrame(info_panel, fg_color="transparent")
        info_right.pack(side="left", fill="both", expand=True, padx=(5, 12), pady=14)
        self.video_title = self._label(info_right, "Aucune vidéo analysée", 18, WHITE, True,
                                       anchor="w", justify="left", wraplength=680)
        self.video_title.pack(anchor="w", fill="x", pady=(4, 9))
        self.video_channel = self._label(info_right, "Le titre et la miniature apparaîtront ici.",
                                          14, MUTED, anchor="w", justify="left")
        self.video_channel.pack(anchor="w", fill="x")
        self.video_stats = self._label(info_right, "", 13, MUTED,
                                        anchor="w", justify="left")
        self.video_stats.pack(anchor="w", fill="x", pady=(12, 0))

        self._label(root, "Format de téléchargement", 16, WHITE, True).pack(
            anchor="w", pady=(0, 7))
        formats = ctk.CTkFrame(root, fg_color="transparent")
        formats.pack(fill="x", pady=(0, 11))
        formats.grid_columnconfigure((0, 1), weight=1, uniform="formats")

        self.video_frame = self._panel(formats)
        self.video_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        video_top = ctk.CTkFrame(self.video_frame, fg_color="transparent")
        video_top.pack(fill="x", padx=13, pady=(11, 3))
        self.video_radio = ctk.CTkRadioButton(
            video_top, text="Vidéo MP4", variable=self.format_var, value="mp4",
            command=self._on_format, font=ctk.CTkFont(family=FONT,size=16,weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=MUTED
        )
        self.video_radio.pack(side="left")
        self.quality_menu = ctk.CTkOptionMenu(
            video_top, values=["Meilleure"], variable=self.quality_var,
            width=125, height=32, fg_color="#202b42",
            button_color="#303d59", button_hover_color="#415274",
            font=ctk.CTkFont(family=FONT,size=12)
        )
        self.quality_menu.pack(side="right")
        self._label(self.video_frame, "Qualité au choix", 12, MUTED).pack(
            anchor="w", padx=43, pady=(0, 10))

        self.audio_frame = self._panel(formats)
        self.audio_frame.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        audio_top = ctk.CTkFrame(self.audio_frame, fg_color="transparent")
        audio_top.pack(fill="x", padx=13, pady=(11, 3))
        self.audio_radio = ctk.CTkRadioButton(
            audio_top, text="Audio MP3", variable=self.format_var, value="mp3",
            command=self._on_format, font=ctk.CTkFont(family=FONT,size=16,weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=MUTED
        )
        self.audio_radio.pack(side="left")
        self._label(audio_top, "320 kb/s", 14, MUTED).pack(side="right", padx=3)
        self._label(self.audio_frame, "Meilleure qualité audio disponible", 12, MUTED).pack(
            anchor="w", padx=43, pady=(0, 10))
        self._on_format()

        progress_panel = self._panel(root)
        progress_panel.pack(fill="x", pady=(0, 12))
        prog_top = ctk.CTkFrame(progress_panel, fg_color="transparent")
        prog_top.pack(fill="x", padx=15, pady=(11, 4))
        self.status_label = self._label(prog_top, "Prêt", 14, WHITE, True, anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.percent_label = self._label(prog_top, "0%", 15, WHITE, True)
        self.percent_label.pack(side="right")
        self.progress_bar = ctk.CTkProgressBar(
            progress_panel, height=13, corner_radius=7,
            progress_color=ACCENT, fg_color="#293448"
        )
        self.progress_bar.pack(fill="x", padx=15, pady=(4, 8))
        stats = ctk.CTkFrame(progress_panel, fg_color="transparent")
        stats.pack(fill="x", padx=15, pady=(0, 11))
        self.bytes_label = self._label(stats, "0 o / —", 12, MUTED)
        self.bytes_label.pack(side="left")
        self.speed_label = self._label(stats, "Vitesse : —", 12, MUTED)
        self.speed_label.pack(side="left", padx=25)
        self.eta_label = self._label(stats, "Temps restant : —", 12, MUTED)
        self.eta_label.pack(side="right")

        bottom = ctk.CTkFrame(root, fg_color="transparent")
        bottom.pack(fill="x")
        self.folder_btn = self._button(bottom, "▣  Ouvrir le dossier", self._open_folder)
        self.folder_btn.pack(side="left", fill="x", expand=True, padx=(0, 9))
        self.next_btn = self._button(bottom, "↻  Suivant", self._next, primary=True)
        self.next_btn.pack(side="left", fill="x", expand=True, padx=(9, 0))

        self._label(root, "Enregistrement automatique : Bureau / ISSA Downloader / mp4 ou mp3",
                    11, MUTED).pack(anchor="center", pady=(9, 0))

    def _on_format(self) -> None:
        video = self.format_var.get() == "mp4"
        if hasattr(self, "quality_menu"):
            self.quality_menu.configure(state="normal" if video else "disabled")
        if hasattr(self, "video_frame"):
            self.video_frame.configure(border_color=ACCENT if video else BORDER)
            self.audio_frame.configure(border_color=BORDER if video else ACCENT)

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status_label.configure(text=message,
                                    text_color=RED if error else WHITE)

    def _reset_progress(self) -> None:
        # A fresh transfer starts at zero. Individual media streams never rewind it.
        self._visible_progress = 0.0
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        self.bytes_label.configure(text="0 o / —")
        self.speed_label.configure(text="Vitesse : —")
        self.eta_label.configure(text="Temps restant : —")

    def _clear_preview(self) -> None:
        self._thumb_ref = None
        self.thumb.configure(image=None, text="Aperçu de la vidéo")
        self.video_title.configure(text="Aucune vidéo analysée")
        self.video_channel.configure(text="Le titre et la miniature apparaîtront ici.")
        self.video_stats.configure(text="")
        self.quality_menu.configure(values=["Meilleure"])
        self.quality_var.set("Meilleure")

    def _update_controls(self) -> None:
        busy = self._mode in {"analyzing", "downloading", "cancelling"}
        active = "disabled" if busy else "normal"
        self.url_entry.configure(state=active)
        self.paste_btn.configure(state=active)
        self.analyze_btn.configure(state=active)
        if self._mode == "downloading":
            self.download_btn.configure(text="×  Annuler", command=self._cancel,
                                         state="normal", fg_color="#914254",
                                         hover_color="#ae566c")
        elif self._mode == "cancelling":
            self.download_btn.configure(text="Annulation...", state="disabled")
        else:
            valid = bool(self._info and self._analyzed_url == utils.normalize_url(self.url_entry.get()))
            self.download_btn.configure(text="↓  Télécharger", command=self._download,
                                         state="normal" if valid and not busy else "disabled",
                                         fg_color=ACCENT, hover_color=ACCENT_HOVER)
        self.folder_btn.configure(state="normal" if self._output and self._mode == "finished"
                                  else "disabled")
        self.next_btn.configure(state="normal" if self._mode == "finished" else "disabled")
        self.video_radio.configure(state=active)
        self.audio_radio.configure(state=active)
        self.quality_menu.configure(state="normal" if not busy and self.format_var.get() == "mp4"
                                    else "disabled")

    def _on_url_change(self) -> None:
        if self._mode in {"analyzing", "downloading", "cancelling"}:
            return
        if self._info and utils.normalize_url(self.url_entry.get()) != self._analyzed_url:
            self._sequence += 1
            self._info = None
            self._analyzed_url = ""
            self._clear_preview()
            self._reset_progress()
            self._mode = "idle"
            self._set_status("Lien modifié — cliquez sur Analyser.")
        self._update_controls()

    def _paste(self) -> None:
        clipboard = utils.paste_from_clipboard(self)
        if clipboard:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard)
            self._on_url_change()
            self.url_entry.focus_set()

    def _enqueue(self, callback, *args) -> None:
        if not self._closing:
            self._queue.put((callback, args))

    def _pump(self) -> None:
        if self._closing:
            return
        for _ in range(40):
            try:
                callback, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except Exception:
                self.log.exception("Interface callback failed")
        self.after(60, self._pump)

    def _analyze(self) -> None:
        if self._mode in {"analyzing", "downloading", "cancelling"}:
            return
        valid, message = utils.validate_url(self.url_entry.get())
        if not valid:
            self._set_status(message, error=True)
            return
        url = utils.normalize_url(self.url_entry.get())
        self._sequence += 1
        seq = self._sequence
        self._mode = "analyzing"
        self._info = None
        self._analyzed_url = ""
        self._output = None
        self._clear_preview()
        self._reset_progress()
        self._set_status("Analyse de la vidéo en cours...")
        self._update_controls()

        def worker():
            try:
                info = self.engine.extract_info(url)
                self._enqueue(self._analysis_done, seq, url, info, None)
            except Exception as exc:
                self._enqueue(self._analysis_done, seq, url, None, str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def _analysis_done(self, seq: int, url: str, info: VideoInfo | None,
                       error: str | None) -> None:
        if seq != self._sequence:
            return
        self._mode = "idle"
        if error or info is None:
            self._set_status("Analyse impossible : " + (error or "erreur inconnue"), error=True)
            self._update_controls()
            return
        self._info, self._analyzed_url = info, url
        self.video_title.configure(text=info.title or "Vidéo sans titre")
        self.video_channel.configure(text=info.uploader or "Chaîne inconnue")
        stats = [utils.format_duration(info.duration)]
        if info.view_count is not None:
            stats.insert(0, f"{utils.format_view_count(info.view_count)} vues")
        if info.upload_date:
            stats.append(utils.format_upload_date(info.upload_date))
        self.video_stats.configure(text="  •  ".join(stats))
        choices = ["Meilleure"] + [q for q in info.formats_summary if q.endswith("p")]
        self.quality_menu.configure(values=choices)
        self.quality_var.set("Meilleure")
        self._set_status("Analyse terminée — choisissez le format puis téléchargez.")
        self._update_controls()
        if info.thumbnail_url:
            self._load_thumbnail(seq, info.thumbnail_url)

    def _load_thumbnail(self, seq: int, url: str) -> None:
        def worker():
            try:
                response = requests.get(url, timeout=12, stream=True)
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    data.extend(chunk)
                    if len(data) > 5_000_000:
                        raise ValueError("Image trop volumineuse")
                with Image.open(io.BytesIO(data)) as im:
                    image = im.convert("RGB")
                    image.thumbnail((480, 270))
                self._enqueue(self._thumbnail_done, seq, image)
            except (OSError, ValueError, requests.RequestException):
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _thumbnail_done(self, seq: int, image: Image.Image) -> None:
        if seq != self._sequence or self._info is None:
            return
        self._thumb_ref = ctk.CTkImage(light_image=image, dark_image=image,
                                        size=(232, 130))
        self.thumb.configure(image=self._thumb_ref, text="")

    def _download(self) -> None:
        # After an MP4 completes, the same analyzed video can be downloaded as
        # MP3 (or another MP4 quality) without pressing Suivant or re-analyzing.
        if self._mode not in {"idle", "finished"} or self._info is None:
            return
        if utils.normalize_url(self.url_entry.get()) != self._analyzed_url:
            self._set_status("Le lien a changé. Cliquez sur Analyser.", error=True)
            return
        fmt = DownloadFormat(self.format_var.get())
        quality_str = self.quality_var.get()
        quality = (int(quality_str[:-1]) if fmt == DownloadFormat.MP4 and
                   quality_str.endswith("p") and quality_str[:-1].isdigit() else None)
        try:
            folder = utils.get_format_output_dir(utils.ensure_downloads_dir(), fmt.value)
        except OSError as exc:
            self._set_status(f"Impossible de créer le dossier : {exc}", error=True)
            return
        url = self._analyzed_url
        self.engine.reset_cancel()
        self._mode = "downloading"
        self._output = None
        self._reset_progress()
        self._set_status("Démarrage du téléchargement...")
        self._update_controls()

        def worker():
            try:
                final = self.engine.download(url, folder, fmt,
                    progress_callback=lambda update: self._enqueue(self._download_progress, update),
                    quality=quality)
                self._enqueue(self._download_done, final, None)
            except Exception as exc:
                self._enqueue(self._download_done, None, str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def _download_progress(self, data: dict) -> None:
        if self._mode not in {"downloading", "cancelling"}:
            return
        percent = monotonic_download_percent(
            self._visible_progress, data.get("percent"), data.get("status")
        )
        self._visible_progress = percent
        self.progress_bar.set(percent / 100)
        self.percent_label.configure(text=f"{percent:.0f}%")
        downloaded = data.get("downloaded_bytes")
        total = data.get("total_bytes")
        self.bytes_label.configure(text=f"{utils.format_bytes(downloaded)} / {utils.format_bytes(total)}")
        self.speed_label.configure(text=f"Vitesse : {utils.format_speed(data.get('speed'))}")
        self.eta_label.configure(text=f"Temps restant : {utils.format_eta(data.get('eta'))}")
        if data.get("status") == "converting":
            self._set_status("Finalisation du fichier (fusion ou conversion)...")
        elif self._mode != "cancelling":
            self._set_status("Téléchargement en cours...")

    def _cancel(self) -> None:
        if self._mode != "downloading":
            return
        self._mode = "cancelling"
        self.engine.request_cancel()
        self._set_status("Annulation en cours...")
        self._update_controls()

    def _download_done(self, output: str | None, error: str | None) -> None:
        if self._closing:
            return
        if error or not output:
            self._mode = "idle"
            if error and "cancel" in error.lower():
                self._set_status("Téléchargement annulé.")
                self._reset_progress()
            else:
                self._set_status("Échec : " + (error or "fichier non trouvé"), error=True)
        else:
            self._output = Path(output)
            self._mode = "finished"
            self._visible_progress = 100.0
            self.progress_bar.set(1)
            self.percent_label.configure(text="100%")
            self._set_status("Téléchargement terminé ! Ouvrez le dossier ou passez au suivant.")
        self._update_controls()

    def _open_folder(self) -> None:
        if not self._output:
            return
        ok, message = utils.open_folder(self._output.parent)
        if not ok:
            self._set_status(message, error=True)

    def _next(self) -> None:
        if self._mode != "finished":
            return
        self._sequence += 1
        self._mode = "idle"
        self._info = None
        self._analyzed_url = ""
        self._output = None
        self.url_entry.delete(0, tk.END)
        self._clear_preview()
        self._reset_progress()
        self._set_status("Prêt pour le lien suivant.")
        self._update_controls()
        self.url_entry.focus_set()

    def on_closing(self) -> None:
        self._closing = True
        self.engine.request_cancel()
        self.destroy()


def run_app() -> None:
    app = ISSADownloaderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
