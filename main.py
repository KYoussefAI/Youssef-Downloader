"""
ISSA Downloader — application entry point.

Run this module directly or compile it with PyInstaller.
"""

from __future__ import annotations

import sys


def self_test() -> int:
    """Headless smoke test for the frozen Windows executable's bundled runtimes."""
    import config
    import utils
    from downloader import DownloaderRuntime
    from app_logging import run_hidden, get_logger

    logger = get_logger()
    ok, reason = utils.check_ffmpeg()
    if not ok:
        logger.error("self-test failed: %s", reason)
        return 10
    if not config.DENO_EXE.is_file():
        logger.error("self-test failed: Deno missing")
        return 11
    try:
        runtime = DownloaderRuntime()
        for command in (
            runtime.command() + ["--version"],
            [str(config.FFMPEG_EXE), "-version"],
            [str(config.FFPROBE_EXE), "-version"],
            [str(config.DENO_EXE), "--version"],
        ):
            result = run_hidden(command, capture_output=True, timeout=30)
            if result.returncode:
                logger.error("self-test binary failed: %s", command[0])
                return 12
    except (OSError, RuntimeError, TimeoutError) as exc:
        logger.error("self-test runtime failed: %s", exc)
        return 13
    logger.info("self-test passed")
    return 0


def main() -> None:
    """
    Bootstrap and launch the ISSA Downloader GUI.

    Ensures required directories exist before the window opens.
    """
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())

    # Lazy imports keep startup slightly faster and aid PyInstaller bundling
    import utils
    import config
    from app_logging import get_logger
    from gui_v3 import run_app

    # Ensure portable folders exist on first launch
    utils.ensure_downloads_dir()
    get_logger().info("application start version=%s frozen=%s", config.APP_VERSION, getattr(sys, "frozen", False))

    try:
        run_app()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
