"""Replaceable yt-dlp process boundary with progress and cancellation support."""
from __future__ import annotations

import json, re, shutil, subprocess, sys, threading, time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import config, utils
from app_logging import get_logger, sanitize, popen_hidden, run_hidden

ProgressCallback = Callable[[dict[str, Any]], None]
PROGRESS, POST, FINAL = "YD_PROGRESS|", "YD_POST|", "YD_FILE|"

class DownloadFormat(str, Enum): MP4 = "mp4"; MP3 = "mp3"
class DownloadStatus(str, Enum):
    IDLE="idle"; ANALYZING="analyzing"; DOWNLOADING="downloading"; CONVERTING="converting"; FINISHED="finished"; ERROR="error"

@dataclass
class VideoInfo:
    title: str=""; uploader: str=""; duration: int|None=None; view_count: int|None=None
    upload_date: str|None=None; thumbnail_url: str|None=None; webpage_url: str=""
    resolution: str=""; description: str=""; id: str=""; formats_summary: list[str]=field(default_factory=list)

@dataclass
class ProgressInfo:
    status: DownloadStatus=DownloadStatus.IDLE; percent: float=0.0
    downloaded_bytes: int|None=None; total_bytes: int|None=None; speed: float|None=None
    eta: int|None=None; message: str=""; output_path: str=""

class DownloaderRuntime:
    def __init__(self): self.log = get_logger()
    def command(self) -> list[str]:
        for path in (config.DOWNLOADER_RUNTIME_DIR/config.YTDLP_EXE_NAME,
                     config.EXE_DIR/"runtime"/config.YTDLP_EXE_NAME,
                     config.RESOURCE_DIR/"runtime"/config.YTDLP_EXE_NAME):
            if path.is_file(): return [str(path)]
        found = shutil.which("yt-dlp")
        if found: return [found]
        if not getattr(sys, "frozen", False):
            try: import yt_dlp  # noqa: F401
            except ImportError: pass
            else: return [sys.executable, "-m", "yt_dlp"]
        raise RuntimeError("yt-dlp runtime is missing. Reinstall the app or use Update downloader.")
    def version(self) -> str:
        try: return run_hidden(self.command()+["--version"], capture_output=True, text=True, timeout=15, check=True).stdout.strip()
        except Exception as exc: self.log.warning("version check failed: %s", sanitize(exc)); return "unavailable"
    def update(self) -> tuple[bool,str]:
        cmd = self.command()
        if len(cmd) != 1: return False, "Source mode: run python -m pip install -U yt-dlp"
        source = Path(cmd[0]).resolve()
        writable = config.DOWNLOADER_RUNTIME_DIR / config.YTDLP_EXE_NAME
        if source != writable.resolve():
            try:
                config.DOWNLOADER_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, writable)
                cmd = [str(writable)]
            except OSError as exc:
                self.log.error("could not stage updater: %s", sanitize(exc))
                return False, "Could not create the writable downloader runtime; the bundled version is unchanged."
        self.log.info("updater start executable=%s", sanitize(cmd[0]))
        try: result = run_hidden(cmd+["--update"], capture_output=True, text=True, timeout=180)
        except Exception as exc: self.log.error("update failed: %s", sanitize(exc)); return False, "Update failed; the existing downloader is unchanged."
        raw = "\n".join((result.stdout,result.stderr)).strip(); self.log.info("updater end exit_code=%s output=%s", result.returncode, sanitize(raw))
        return (False,"Update failed; the existing downloader is unchanged. See the log.") if result.returncode else (True, raw.splitlines()[-1] if raw else "Downloader updated.")

class YouTubeDownloader:
    def __init__(self, runtime: DownloaderRuntime|None=None):
        self.runtime=runtime or DownloaderRuntime(); self.log=get_logger(); self._cancel_requested=False
        self._process: subprocess.Popen[str]|None=None; self._current_info: VideoInfo|None=None
        self.log.info("downloader initialized app=%s", config.APP_VERSION)
    @property
    def current_info(self): return self._current_info
    @property
    def ytdlp_version(self): return self.runtime.version()
    def update_downloader(self): return self.runtime.update()
    def reset_cancel(self): self._cancel_requested=False
    def request_cancel(self):
        self._cancel_requested=True
        if self._process and self._process.poll() is None:
            if sys.platform == "win32":
                run_hidden(["taskkill", "/PID", str(self._process.pid), "/T", "/F"], capture_output=True)
            else:
                self._process.terminate()

    @staticmethod
    def _common():
        args = ["--no-playlist","--no-config","--encoding","utf-8"]
        if config.DENO_EXE.is_file(): args += ["--js-runtimes",f"deno:{config.DENO_EXE}"]
        return args
    def extract_info(self,url: str) -> VideoInfo:
        valid, reason = utils.validate_url(url)
        if not valid: raise ValueError(reason)
        url=utils.normalize_url(url); raw=self._capture(self.runtime.command()+self._common()+["--dump-single-json","--skip-download",url],url,"analysis")
        try: data=json.loads(raw)
        except json.JSONDecodeError as exc: self._fail(f"Invalid metadata JSON: {exc}\n{raw}",url,"analysis")
        info=self._parse_info(data); self._current_info=info; return info
    def download(self,url: str,output_dir: Path,fmt: DownloadFormat,progress_callback: ProgressCallback|None=None) -> str:
        if self._cancel_requested: raise RuntimeError("Download cancelled.")
        valid, reason = utils.validate_url(url)
        if not valid: raise ValueError(reason)
        url=utils.normalize_url(url); output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
        ok,msg=utils.check_ffmpeg()
        if not ok: self.log.error("category=ffmpeg_missing %s",sanitize(msg)); raise RuntimeError(msg)
        cmd=self.runtime.command()+self._common()+["--ffmpeg-location",utils.get_ffmpeg_location(),"--output",str(output_dir/"%(title).180B [%(id)s].%(ext)s"),
            "--retries","10","--fragment-retries","10","--file-access-retries","3","--retry-sleep","http:exp=1:20","--retry-sleep","fragment:exp=1:10",
            "--socket-timeout","20","--concurrent-fragments","4","--continue","--part","--newline","--progress",
            "--progress-template",f"download:{PROGRESS}%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s|%(progress._percent_str)s",
            "--progress-template",f"postprocess:{POST}%(progress.status)s",
            "--print",f"after_move:{FINAL}%(filepath)s"]
        cmd += (["--format",config.MP4_FORMAT,"--merge-output-format","mp4"] if fmt==DownloadFormat.MP4 else ["--format",config.MP3_FORMAT,"--extract-audio","--audio-format","mp3","--audio-quality",config.MP3_BITRATE+"K"]); cmd.append(url)
        self.log.info("download video=%s format=%s yt-dlp=%s",self._video_id(url),fmt.value,self.runtime.version())
        return self._download_process(cmd,url,output_dir,fmt,progress_callback)

    def _capture(self,cmd,url,operation):
        try: r=run_hidden(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90)
        except Exception as exc: self._fail(str(exc),url,operation)
        if r.returncode: self._fail("\n".join((r.stdout,r.stderr)),url,operation)
        if r.stderr.strip(): self.log.info("%s diagnostics video=%s raw=%s",operation,self._video_id(url),sanitize(r.stderr))
        return r.stdout.strip()
    def _download_process(self,cmd,url,output_dir,fmt,callback):
        # Keep a bounded diagnostic tail: a long transfer must not use unbounded RAM.
        out=deque(maxlen=250); final=""; started=time.time()
        if self._cancel_requested:
            raise RuntimeError("Download cancelled.")
        process=popen_hidden(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,encoding="utf-8",errors="replace",bufsize=1)
        self._process=process
        try:
            if self._cancel_requested:
                self.request_cancel()
            assert process.stdout is not None
            for line in process.stdout:
                line=line.rstrip("\r\n")
                if line.startswith(PROGRESS):
                    if callback: callback(self._progress(line[len(PROGRESS):]))
                elif line.startswith(POST):
                    if callback: callback({"status":"converting","percent":99.0,
                                          "message":"Merging video and audio..." if fmt==DownloadFormat.MP4 else "Converting to MP3..."})
                elif line.startswith(FINAL):
                    final=line[len(FINAL):]
                else:
                    out.append(line)
            rc=process.wait()
        finally:
            if process.stdout: process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            self._process=None
        raw="\n".join(out)
        self.log.info("subprocess exit pid=%s exit_code=%s",process.pid,rc)
        if self._cancel_requested:
            raise RuntimeError("Download cancelled.")
        if rc: self._fail(raw,url,"download")
        if not final or not Path(final).is_file():
            final=self._fallback_output(Path(output_dir),fmt,started)
        if not final: self._fail(raw+"\nProcess exited 0 but final output could not be located",url,"download")
        if callback: callback({"status":"finished","percent":100.0,"message":"Finished","output_path":final})
        return str(Path(final).resolve())
    @staticmethod
    def _num(value,kind=float):
        try: return kind(re.sub(r"[^0-9.\-]","",value)) if value.strip() not in {"","NA","N/A","None"} else None
        except (ValueError,TypeError): return None
    def _progress(self,payload):
        p=(payload.split("|")+[""]*6)[:6]
        total=self._num(p[1],int) or self._num(p[2],int)
        return {"status":"downloading","percent":max(0.0,min(100.0,self._num(p[5]) or 0.0)),"downloaded_bytes":self._num(p[0],int),"total_bytes":total,"speed":self._num(p[3]),"eta":self._num(p[4],int),"message":"Downloading..."}
    @staticmethod
    def _fallback_output(output_dir,fmt,started):
        extension=".mp4" if fmt==DownloadFormat.MP4 else ".mp3"
        candidates=[p for p in output_dir.glob(f"*{extension}") if p.is_file() and p.stat().st_mtime >= started-2 and ".part" not in p.name and not re.search(r"\.f\d+\.",p.name)]
        return str(max(candidates,key=lambda p:p.stat().st_mtime).resolve()) if candidates else ""
    def _fail(self,raw,url,operation):
        category,friendly=utils.classify_error(raw); self.log.error("%s video=%s category=%s raw=%s",operation,self._video_id(url),category,sanitize(raw)); raise RuntimeError(friendly)
    @staticmethod
    def _video_id(url):
        p=urlparse(url); return ((parse_qs(p.query).get("v") or [p.path.rstrip("/").split("/")[-1]])[0] or "unknown")[:20]
    @staticmethod
    def _parse_info(raw):
        heights=sorted({int(f["height"]) for f in raw.get("formats") or [] if f.get("height") and f.get("vcodec","none")!="none"},reverse=True)
        thumbs=raw.get("thumbnails") or []; height=raw.get("height") or (heights[0] if heights else None)
        return VideoInfo(raw.get("title") or "Unknown Title",raw.get("uploader") or raw.get("channel") or "Unknown",raw.get("duration"),raw.get("view_count"),raw.get("upload_date"),raw.get("thumbnail") or (thumbs[-1].get("url") if thumbs else None),raw.get("webpage_url") or raw.get("original_url") or "",f"{height}p" if height else "Unknown",raw.get("description") or "",raw.get("id") or "",[f"{h}p" for h in heights])
