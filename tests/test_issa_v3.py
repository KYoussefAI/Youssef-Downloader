"""Regression tests for the French v3 download format and Windows packaging."""
import unittest
import tempfile
from pathlib import Path
from unittest import mock
import config
import utils
from downloader import DownloadFormat, YouTubeDownloader

VIDEO = "https://www.youtube.com/watch?v=abcdefghijk"

class V3Tests(unittest.TestCase):
    def make_engine(self):
        engine = YouTubeDownloader.__new__(YouTubeDownloader)
        engine.runtime = mock.Mock()
        engine.runtime.command.return_value = ["yt-dlp"]
        engine.runtime.version.return_value = "2026-test"
        engine._cancel_requested = False
        engine._process = None
        engine.log = mock.Mock()
        return engine

    def test_mp4_resolution_limit_is_forwarded(self):
        engine = self.make_engine()
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(utils,"check_ffmpeg", return_value=(True,"")), \
             mock.patch.object(engine,"_download_process",return_value="ok") as process:
            engine.download(VIDEO,Path(folder),DownloadFormat.MP4,quality=720)
            command=process.call_args.args[0]
            self.assertIn("bestvideo[height<=720]", " ".join(command))
            self.assertIn("--merge-output-format", command)

    def test_mp3_without_resolution(self):
        engine = self.make_engine()
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(utils,"check_ffmpeg",return_value=(True,"")), \
             mock.patch.object(engine,"_download_process",return_value="ok") as process:
            engine.download(VIDEO,Path(folder),DownloadFormat.MP3,quality=None)
            command=process.call_args.args[0]
            self.assertIn("--extract-audio",command)
            self.assertIn("--audio-format",command)

    def test_quality_guard(self):
        engine = self.make_engine()
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(utils,"check_ffmpeg",return_value=(True,"")):
            with self.assertRaisesRegex(ValueError,"Qualité"):
                engine.download(VIDEO,Path(folder),DownloadFormat.MP4,quality=99999)

    def test_issa_desktop_folders(self):
        self.assertEqual(config.DOWNLOADS_DIR.name,"ISSA Downloader")
        with tempfile.TemporaryDirectory() as folder:
            for f in ("mp4","mp3"):
                sub = utils.get_format_output_dir(Path(folder),f)
                self.assertEqual(sub.name,f)
                self.assertTrue(sub.is_dir())

if __name__ == "__main__":
    unittest.main()
