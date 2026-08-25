"""
Youssef Downloader — application entry point.

Run this module directly or compile it with PyInstaller.
"""

from __future__ import annotations

import sys


def main() -> None:
    """
    Bootstrap and launch the Youssef Downloader GUI.

    Ensures required directories exist before the window opens.
    """
    # Lazy imports keep startup slightly faster and aid PyInstaller bundling
    import utils
    import config
    from app_logging import get_logger
    from gui import run_app

    # Ensure portable folders exist on first launch
    utils.ensure_downloads_dir()
    get_logger().info("application start version=%s frozen=%s", config.APP_VERSION, getattr(sys, "frozen", False))

    try:
        run_app()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
