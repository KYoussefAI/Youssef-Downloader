"""Credential-sanitizing rotating log and hidden subprocess helpers."""
from __future__ import annotations
import logging, re, subprocess, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Sequence
import config

_LOGGER_NAME = "youssef_downloader"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(po[_ -]?token(?:=|:|\+))[^\s;,&]+"),
    re.compile(r"(?i)(authorization:\s*)[^\r\n]+"),
    re.compile(r"(?i)(cookie(?:s)?(?:=|:)\s*)[^\r\n]+"),
)

def sanitize(text: object) -> str:
    value = str(text)
    for pattern in _SECRET_PATTERNS: value = pattern.sub(r"\1<redacted>", value)
    return value

def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers: return logger
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(config.LOG_DIR/"app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler); logger.setLevel(logging.INFO); logger.propagate = False
    return logger

def log_path() -> Path: return config.LOG_DIR/"app.log"

def hidden_subprocess_kwargs() -> dict[str, Any]:
    if sys.platform != "win32": return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": startupinfo}

def run_hidden(args: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]; log = get_logger()
    log.info("subprocess run start executable=%s args=%s", sanitize(command[0]), sanitize(" ".join(command[1:])))
    options = hidden_subprocess_kwargs(); options.update(kwargs); options["shell"] = False
    result = subprocess.run(command, **options)
    log.info("subprocess run end executable=%s exit_code=%s", sanitize(command[0]), result.returncode)
    return result

def popen_hidden(args: Sequence[str], **kwargs: Any) -> subprocess.Popen[str]:
    command = [str(arg) for arg in args]; log = get_logger()
    log.info("subprocess start executable=%s args=%s", sanitize(command[0]), sanitize(" ".join(command[1:])))
    options = hidden_subprocess_kwargs(); options.update(kwargs); options["shell"] = False
    process = subprocess.Popen(command, **options)
    log.info("subprocess started executable=%s pid=%s", sanitize(command[0]), process.pid)
    return process
