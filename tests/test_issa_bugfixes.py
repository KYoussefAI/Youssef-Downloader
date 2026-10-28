"""Regression tests for progress rewind and MP4 -> MP3 on the same URL."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from progress_tracking import monotonic_download_percent
from downloader import DownloadFormat

URL = "https://www.youtube.com/watch?v=abcdefghijk"


class ProgressTrackerTests(unittest.TestCase):
    def test_never_moves_backwards_on_repeated_streams(self):
        samples = [1, 2, 3, 4, 3, 4, 5, 6, 5, 6, 7, 98, 1, 14, 75, 100]
        display = 0.0
        values = []
        for raw in samples:
            display = monotonic_download_percent(display, raw, "downloading")
            values.append(display)
        self.assertEqual(values[:11], [1, 2, 3, 4, 4, 4, 5, 6, 6, 6, 7])
        self.assertEqual(values[-1], 98)
        self.assertEqual(values, sorted(values))

    def test_conversion_and_completion_never_rewind(self):
        pct = 0
        for value, status in [(20, "downloading"), (100, "downloading"),
                              (50, "downloading"), (0, "converting"),
                              (30, "downloading"), (100, "finished")]:
            upcoming = monotonic_download_percent(pct, value, status)
            self.assertGreaterEqual(upcoming, pct)
            pct = upcoming
        self.assertEqual(pct, 100)
        self.assertEqual(monotonic_download_percent(0, 1), 1)

    def test_invalid_numbers_are_ignored(self):
        for v in (None, "NA", float("nan"), float("inf"), -4):
            self.assertEqual(monotonic_download_percent(42.5, v), 42.5)


class FormatSwitchTests(unittest.TestCase):
    def test_completed_mp4_can_start_mp3_without_reanalyze(self):
        # Exercise real GUI handler logic without launching a Tk window.
        from gui_v3 import ISSADownloaderApp
        app = mock.Mock()
        app._mode = "finished"
        app._info = object()
        app._analyzed_url = URL
        app.url_entry.get.return_value = URL
        app.format_var.get.return_value = "mp3"
        app.quality_var.get.return_value = "Meilleure"
        app._output = Path("previous.mp4")
        app.engine.download.return_value = "next.mp3"
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("gui_v3.utils.ensure_downloads_dir", return_value=Path(tmp)), \
             mock.patch("gui_v3.threading.Thread") as thread:
            ISSADownloaderApp._download(app)
            self.assertEqual(app._mode, "downloading")
            self.assertIsNone(app._output)
            self.assertEqual(thread.call_count, 1)
            thread.call_args.kwargs["target"]()
            self.assertEqual(app.engine.download.call_count, 1)
            args, kwargs = app.engine.download.call_args
            self.assertEqual(args[0], URL)
            self.assertEqual(args[2], DownloadFormat.MP3)
            self.assertEqual(args[1], Path(tmp) / "mp3")
            self.assertIsNone(kwargs["quality"])
            app._reset_progress.assert_called_once()
            app._update_controls.assert_called_once()

    def test_stale_url_cannot_reuse_old_analysis(self):
        from gui_v3 import ISSADownloaderApp
        app = mock.Mock()
        app._mode = "finished"
        app._info = object()
        app._analyzed_url = URL
        app.url_entry.get.return_value = "https://youtu.be/12345678901"
        ISSADownloaderApp._download(app)
        app.engine.download.assert_not_called()
        app._set_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
