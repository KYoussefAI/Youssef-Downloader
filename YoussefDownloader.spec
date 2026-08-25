# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)
import config

block_cipher = None

version_parts = tuple(int(part) for part in config.APP_VERSION.split('.'))
version_tuple = (version_parts + (0, 0, 0, 0))[:4]
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple,
                      mask=0x3F, flags=0x0, OS=0x40004, fileType=0x1,
                      subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', config.APP_PUBLISHER),
            StringStruct('FileDescription', config.APP_DESCRIPTION),
            StringStruct('FileVersion', config.APP_VERSION),
            StringStruct('InternalName', 'YoussefDownloader'),
            StringStruct('LegalCopyright', config.APP_COPYRIGHT),
            StringStruct('OriginalFilename', config.APP_EXECUTABLE),
            StringStruct('ProductName', config.APP_TITLE),
            StringStruct('ProductVersion', config.APP_VERSION),
        ])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)

# Collect all required data files and submodules
ctk_datas = collect_data_files('customtkinter')
ctk_submodules = collect_submodules('customtkinter')

datas = [
    ('assets', 'assets'),
    ('ffmpeg', 'ffmpeg'),
    ('runtime/DENO_LICENSE.md', 'runtime'),
] + ctk_datas

binaries = [
    ('ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin'),
    ('ffmpeg/bin/ffprobe.exe', 'ffmpeg/bin'),
    ('runtime/yt-dlp.exe', 'runtime'),
    ('runtime/deno.exe', 'runtime'),
]

hiddenimports = [
    'PIL',
    'PIL.Image',
    'PIL.PngImagePlugin',
    'PIL.JpegImagePlugin',
    'PIL._tkinter_finder',
    'customtkinter',
    'tkinter',
    'tkinter.filedialog',
    'requests',
    'urllib3',
] + ctk_submodules

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['yt_dlp'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YoussefDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YoussefDownloader',
)
