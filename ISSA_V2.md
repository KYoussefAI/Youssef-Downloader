# ISSA Downloader v2

Refreshed Windows branding and reliability improvements.

## Changes
- Strict hostname and 11-character video-ID checks; phishing-style lookalike URLs rejected.
- HTTPS certificate verification remains enabled.
- Bounded diagnostics memory during long downloads.
- Avoids discarding a cancellation request at download start.
- Thread-to-GUI communication uses a main-thread queue rather than worker calls into Tk.
- Thumbnail responses have a size limit; stale thumbnail updates are discarded.
- Download folder and MP3/MP4 choice persist between launches.
- The completed file can be opened directly.
- Video output names include unique video identifiers to avoid accidental collisions.
- ISSA branding generated consistently in PNG and ICO formats.

## Build on Windows
Run:
```powershell
python -m pip install -r requirements-build.txt
python tools/generate_brand.py
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean ISSA.spec
```
Application: `dist/ISSA/ISSA.exe`. Keep the complete `dist/ISSA` directory when sharing it.

Alternatively, use GitHub Actions **ISSA Windows EXE** on the branch. Download its `ISSA-Downloader-Windows` artifact. The result is a folder-based Windows portable executable, not a single-file EXE.

This work does not bypass DRM, authentication, private-video access, or YouTube access restrictions. No live network download integration tests were run; perform an end-to-end smoke test on Windows before shipping.
