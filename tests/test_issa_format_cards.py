"""User-reported regression: selecting MP3 after a successful MP4 must re-arm Download."""
import unittest
from pathlib import Path
from unittest import mock

from gui_v3 import ISSADownloaderApp

LINK = "https://www.youtube.com/watch?v=abcdefghijk"


class ReusableFormatCardTests(unittest.TestCase):
    def test_clicking_entire_mp3_card_rearms_completed_mp4(self):
        app = mock.Mock()
        app._mode = "finished"
        app._info = object()
        app._output = Path("Bureau/ISSA Downloader/mp4/saved.mp4")
        app.format_var.get.return_value = "mp4"

        ISSADownloaderApp._select_format(app, "mp3")

        app.format_var.set.assert_called_once_with("mp3")
        self.assertEqual(app._mode, "idle")
        self.assertIsNotNone(app._info)
        self.assertEqual(app._output.suffix, ".mp4")  # Previous file remains accessible
        app._reset_progress.assert_called_once()
        app._update_controls.assert_called_once()
        app._set_status.assert_called_once()
        self.assertIn("audio MP3", app._set_status.call_args.args[0])

    def test_clicking_mp4_card_after_mp3_rearms_too(self):
        app = mock.Mock()
        app._mode = "finished"
        app._info = object()
        app._output = Path("song.mp3")
        ISSADownloaderApp._select_format(app, "mp4")
        self.assertEqual(app._mode, "idle")
        app.format_var.set.assert_called_once_with("mp4")

    def test_cards_cannot_change_during_active_download(self):
        for busy in ("analyzing", "downloading", "cancelling"):
            with self.subTest(busy=busy):
                app = mock.Mock()
                app._mode = busy
                ISSADownloaderApp._select_format(app, "mp3")
                app.format_var.set.assert_not_called()
                self.assertEqual(app._mode, busy)

    def test_download_action_enabled_after_selecting_new_format(self):
        app = mock.Mock()
        app._mode = "idle"
        app._info = object()
        app._analyzed_url = LINK
        app.url_entry.get.return_value = LINK
        app.format_var.get.return_value = "mp3"
        app._output = Path("video.mp4")
        ISSADownloaderApp._update_controls(app)
        kwargs = app.download_btn.configure.call_args.kwargs
        self.assertEqual(kwargs["state"], "normal")
        self.assertEqual(kwargs["text"], "↓  Télécharger")
        app.folder_btn.configure.assert_called_once_with(state="normal")
        app.next_btn.configure.assert_called_once_with(state="normal")
        app.video_frame.configure.assert_called_once_with(state="normal")
        app.audio_frame.configure.assert_called_once_with(state="normal")

    def test_no_tiny_radio_buttons_in_form_cards(self):
        import inspect
        source = inspect.getsource(ISSADownloaderApp._build)
        self.assertNotIn("CTkRadioButton", source)
        self.assertIn('command=lambda: self._select_format("mp3")', source)
        self.assertIn('command=lambda: self._select_format("mp4")', source)


if __name__ == "__main__":
    unittest.main()
