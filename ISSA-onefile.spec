# -*- mode: python ; coding: utf-8 -*-
# Fully self-contained executable: FFmpeg, yt-dlp and Deno extract to PyInstaller _MEIPASS.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo
)
import config
version = tuple(int(part) for part in config.APP_VERSION.split("."))
version = (version + (0, 0, 0, 0))[:4]
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version, prodvers=version, mask=0x3F,
                      flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", config.APP_PUBLISHER),
            StringStruct("FileDescription", config.APP_DESCRIPTION),
            StringStruct("FileVersion", config.APP_VERSION),
            StringStruct("OriginalFilename", "ISSA.exe"),
            StringStruct("ProductName", config.APP_TITLE),
            StringStruct("ProductVersion", config.APP_VERSION)
        ])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])])
    ]
)
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[
        ("ffmpeg/bin/ffmpeg.exe", "ffmpeg/bin"),
        ("ffmpeg/bin/ffprobe.exe", "ffmpeg/bin"),
        ("runtime/yt-dlp.exe", "runtime"),
        ("runtime/deno.exe", "runtime")
    ],
    datas=[("assets", "assets"), ("runtime/DENO_LICENSE.md", "runtime")]
          + collect_data_files("customtkinter"),
    hiddenimports=["PIL", "PIL.Image", "PIL.PngImagePlugin",
                   "PIL.JpegImagePlugin", "PIL._tkinter_finder",
                   "tkinter", "requests", "urllib3"]
                  + collect_submodules("customtkinter"),
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["yt_dlp"], noarchive=False
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="ISSA", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    icon="assets/issa.ico", version=version_info
)
