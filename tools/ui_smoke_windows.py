"""Native Windows smoke test for the actual CustomTkinter buttons, no internet required."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from downloader import DownloadFormat, VideoInfo
from gui_v3 import ISSADownloaderApp

URL = "https://www.youtube.com/watch?v=abcdefghijk"


def main() -> None:
    app = ISSADownloaderApp()
    app.withdraw()
    try:
        app.url_entry.insert(0, URL)
        app._info = VideoInfo(title="Mock video")
        app._analyzed_url = URL
        app._output = Path("previous.mp4")
        app._mode = "finished"
        app._update_controls()

        assert app.download_btn.cget("state") == "normal", "Download button not enabled at completion"
        assert app.audio_frame.cget("state") == "normal", "MP3 card not clickable"

        # Native full rectangle button invokes same handler as an actual user click.
        app.audio_frame.cget("command")()
        assert app.format_var.get() == "mp3", "MP3 selection did not register"
        assert app._mode == "idle", "MP3 selection did not rearm completed download"
        assert app.download_btn.cget("state") == "normal", "Download button still disabled after MP3 selection"

        with TemporaryDirectory() as tmp, \
             mock.patch("gui_v3.utils.ensure_downloads_dir", return_value=Path(tmp)), \
             mock.patch("gui_v3.threading.Thread") as thread:
            app.download_btn.cget("command")()
            assert app._mode == "downloading", "Download button click did not launch download"
            assert thread.call_count == 1, "A download thread was not created"
            target = thread.call_args.kwargs["target"]
            app.engine.download = mock.Mock(return_value=str(Path(tmp) / "example.mp3"))
            target()
            app._pump()
            app.engine.download.assert_called_once()
            args, kwargs = app.engine.download.call_args
            assert args[0] == URL
            assert args[2] == DownloadFormat.MP3
            assert args[1] == Path(tmp) / "mp3"
            assert app._mode == "finished"
            assert app.download_btn.cget("state") == "normal", "Download action not reenabled after MP3"
        print(f"ISSA {config.APP_VERSION}: native MP4 -> MP3 card and Download button smoke test passed")
    finally:
        app.on_closing()


if __name__ == "__main__":
    main()
