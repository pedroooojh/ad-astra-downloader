# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

bin_files = []
for name in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"):
    path = Path("bin") / name
    if path.exists():
        bin_files.append((str(path), "bin"))

a = Analysis(
    ["app.py"], pathex=[], binaries=bin_files,
    datas=[
        ("assets/adastra.png", "assets"),
        ("assets/folder.svg", "assets"),
    ], hiddenimports=[], hookspath=[]
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="Ad Astra Downloader", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, console=False,
    icon="assets/adastra.ico",
)
