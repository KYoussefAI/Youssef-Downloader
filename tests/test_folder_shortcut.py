"""The downloads root is always available, independent of download state."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import config
from gui_v3 import ISSADownloaderApp


class FolderButtonTests(unittest.TestCase):
    def test_button_enabled_in_every_state(self):
        for mode in ("idle", "analyzing", "downloading", "cancelling", "finished"):
            for output in (None, Path("downloaded.mp4")):
                with self.subTest(mode=mode, output=output):
                    app = mock.Mock()
                    app._mode = mode
                    app._info = None
                    app._output = output
                    app.format_var.get.return_value = "mp4"
                    ISSADownloaderApp._update_controls(app)
                    app.folder_btn.configure.assert_called_once_with(state="normal")

    def test_open_root_folder_not_specific_format_folder(self):
        app = mock.Mock()
        app._output = Path("other/place/mp3/previous.mp3")
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch("gui_v3.utils.ensure_downloads_dir", return_value=root) as created, \
                 mock.patch("gui_v3.utils.open_folder", return_value=(True, "")) as opened:
                ISSADownloaderApp._open_folder(app)
                created.assert_called_once()
                opened.assert_called_once_with(root)
                app._set_status.assert_not_called()

    def test_missing_directory_is_created_with_both_subdirectories(self):
        import utils
        with TemporaryDirectory() as temp:
            expected = Path(temp) / "ISSA Downloader"
            with mock.patch.object(config, "DOWNLOADS_DIR", expected):
                created = utils.ensure_downloads_dir()
            self.assertEqual(created, expected)
            self.assertTrue((created / "mp4").is_dir())
            self.assertTrue((created / "mp3").is_dir())

    def test_errors_are_visible(self):
        app = mock.Mock()
        with mock.patch("gui_v3.utils.ensure_downloads_dir", side_effect=OSError("Permission denied")):
            ISSADownloaderApp._open_folder(app)
        self.assertTrue(app._set_status.call_args.kwargs["error"])
        self.assertIn("Permission denied", app._set_status.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
