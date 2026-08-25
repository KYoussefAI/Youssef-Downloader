# Youssef Downloader

A modern, portable Windows desktop application for downloading YouTube videos and audio. Built with Python, CustomTkinter, and yt-dlp.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

- **Modern dark UI** — Clean CustomTkinter interface with rounded widgets
- **Video analysis** — Preview title, uploader, duration, resolution, views, and thumbnail before downloading
- **MP4 downloads** — Highest-quality video merged with best audio into MP4
- **MP3 extraction** — Highest-quality audio converted to 320 kbps MP3
- **Live progress** — Percentage, speed, ETA, and file size during download
- **Portable design** — Bundled FFmpeg; no system PATH configuration required
- **Non-blocking** — All downloads run on background threads; the GUI stays responsive
- **PyInstaller ready** — Compile to a standalone `.exe` with one command

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.11 or later |
| FFmpeg | Bundled in `ffmpeg/bin/` |
| Internet | Required for analysis and download |

### Python packages

```
customtkinter
yt-dlp>=2026.08.19
Pillow
requests
```

---

## Installation

### 1. Clone or download the project

```
Youssef Downloader/
├── assets/
├── ffmpeg/bin/
├── installer/
├── runtime/
├── tests/
├── config.py
├── downloader.py
├── gui.py
├── utils.py
├── main.py
├── build_installer.ps1
├── YoussefDownloader.spec
├── requirements.txt
├── requirements-build.txt
└── README.md
```

### 2. Install Python dependencies

Open a terminal in the project folder and run:

```powershell
python -m pip install -r requirements.txt
```

### 3. Add FFmpeg (required for MP4 merge and MP3 conversion)

Download FFmpeg for Windows from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (or [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/)) and place these files in the `ffmpeg/bin/` folder:

```
ffmpeg/
└── bin/
    ├── ffmpeg.exe
    └── ffprobe.exe
```

The application automatically uses the bundled copy — no PATH setup needed.

### 4. Run the application

```powershell
python main.py
```

---

## Usage

1. **Paste** a YouTube URL into the text box (or click **Paste** from clipboard).
2. Click **Analyze** to fetch video metadata and preview the thumbnail.
3. Choose **MP4 Video** or **MP3 Audio**.
4. Set the **Download Location**. It defaults to `Desktop\Youssef Downloader`
   (including a OneDrive-redirected Desktop when present).
5. Click **Download** and monitor progress in real time.

---

## Downloader runtime and updates

The GUI invokes the official `runtime/yt-dlp.exe` as a separate process. The
**Update downloader** button runs yt-dlp's official updater; a YouTube extractor
fix therefore does not require rebuilding the GUI. Updates are never attempted
automatically at startup. Source execution can fall back to `python -m yt_dlp`.

The bundled runtime must come only from an official yt-dlp release and must be
verified against that release's `SHA2-256SUMS`. Logs rotate under
`%LOCALAPPDATA%\Youssef Downloader\logs` and redact cookies and PO Tokens.

PO Tokens are not hardcoded. For affected networks, install a provider through
yt-dlp's official plugin mechanism (for example the provider recommended in the
yt-dlp PO Token guide) and install its documented current Node.js or Deno runtime.
Ordinary public videos do not require cookies.

The release bundles the official Deno 2.8.1 Windows runtime for yt-dlp's
YouTube JavaScript challenge support. Deno is distributed under the MIT license;
the bundled license text is stored at `runtime/DENO_LICENSE.md`.

## Building a Standalone Executable

Install the application and build dependencies:

```powershell
python -m pip install -r requirements-build.txt
```

Build the application folder (includes independently updateable yt-dlp.exe):

```powershell
python -m PyInstaller --noconfirm --clean YoussefDownloader.spec
```

The compiled folder is `dist-app/YoussefDownloader/`. Keep that folder intact. The
first successful update is stored in the user-writable runtime directory and is
preferred over the bundled fallback.

## Building the Windows installer

Install Python 3.11+ and Inno Setup 6, then run from the repository root:

```powershell
.\build_installer.ps1
```

The script verifies the checked-in yt-dlp and Deno SHA-256 checksums, installs
the dependencies in `requirements-build.txt`, creates and validates the
PyInstaller onedir application, and then compiles the Inno Setup installer. It
produces:

```text
dist-installer\YoussefDownloader-Setup.exe
```

For a signed release, Authenticode-sign the packaged application executable
before Inno Setup runs and sign the final setup executable afterward. Unsigned
local builds remain supported.

### PyInstaller notes

- The app detects frozen execution via `sys.frozen` and resolves paths relative to the executable.
- Include `assets/` and `ffmpeg/` as bundled data directories.
- Test the `.exe` on a machine without Python installed before distributing.

---

## Project Structure

| File / Folder | Purpose |
|---------------|---------|
| `main.py` | Application entry point |
| `gui.py` | CustomTkinter user interface |
| `downloader.py` | yt-dlp metadata extraction and download engine |
| `utils.py` | URL validation, formatting, filesystem helpers |
| `config.py` | Paths, constants, frozen-executable detection |
| `assets/` | Application icon and logo |
| `app_logging.py` | Rotating, redacted application logging |
| `ffmpeg/bin/` | Bundled FFmpeg and FFprobe binaries |
| `runtime/` | Bundled yt-dlp and Deno runtimes, checksums, and Deno license |
| `tests/` | Unit test suite |
| `YoussefDownloader.spec` | PyInstaller onedir build definition |
| `build_installer.ps1` | Verified application and installer build pipeline |
| `installer/` | Inno Setup installer definition |
| `requirements.txt` | Python package dependencies |
| `requirements-build.txt` | Application plus PyInstaller build dependencies |

Downloaded media is written outside the repository by default, under
`Desktop\Youssef Downloader` in the current user's profile.

---

## Tests

Run the unit test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   gui.py    │────▶│ downloader.py│────▶│   yt-dlp    │
│ (CustomTk)  │◀────│  (engine)    │◀────│  + FFmpeg   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
   utils.py             config.py
```

- **UI layer** (`gui.py`) — Handles layout, user input, and thread-safe progress updates.
- **Engine layer** (`downloader.py`) — Wraps yt-dlp for analysis and downloading.
- **Utilities** (`utils.py`) — Shared helpers with no UI or download dependencies.
- **Configuration** (`config.py`) — Single source of truth for paths and constants.

All downloads run on background threads. UI updates are scheduled on the main thread via `after()` to prevent freezing.

---

## Error Handling

The application handles common failure cases gracefully:

| Scenario | User Message |
|----------|-------------|
| Invalid URL | Friendly validation prompt |
| Network failure | Check internet connection |
| Video unavailable | Video removed or region-blocked |
| Age-restricted | Requires sign-in |
| Private video | Cannot be downloaded |
| Missing FFmpeg | Instructions to add binaries |

---

## Extending the Application

- **New formats** — Add entries to `DownloadFormat` in `downloader.py` and corresponding yt-dlp options.
- **Playlists** — Set `noplaylist: False` in yt-dlp options (currently disabled).
- **Quality picker** — Extend the analyze step to populate a resolution dropdown from `VideoInfo.formats_summary`.
- **Themes** — Adjust `ctk.set_appearance_mode()` and color values in `gui.py`.

---

## License

[MIT License](LICENSE) — Copyright (c) 2026 Youssef.

---

## Disclaimer

This tool is for personal use only. Respect copyright laws and YouTube's Terms of Service. The authors are not responsible for misuse.
