import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config, utils
from downloader import DownloadFormat, DownloaderRuntime, YouTubeDownloader
import app_logging


class ErrorClassificationTests(unittest.TestCase):
    def assert_category(self, text, expected): self.assertEqual(utils.classify_error(text)[0], expected)
    def test_specific_errors(self):
        cases = {
            "ERROR: unable to download video data: HTTP Error 403: Forbidden": "http_403",
            "HTTP Error 429: Too Many Requests": "http_429",
            "getaddrinfo failed": "network",
            "This is a private video": "private",
            "Sign in to confirm you’re not a bot": "bot_verification",
            "No PO Token provider available": "po_token",
            "ffmpeg exited with code 1": "ffmpeg",
            "fragment 12 not found, fragment failed": "fragment",
            "nsig extraction failed; URL has expired": "extraction",
        }
        for raw, category in cases.items():
            with self.subTest(raw=raw): self.assert_category(raw, category)
    def test_generic_wrapper_is_not_network(self):
        self.assertNotEqual(utils.classify_error("unable to download video data")[0], "network")


class DownloaderTests(unittest.TestCase):
    def test_windows_subprocesses_are_hidden(self):
        options = app_logging.hidden_subprocess_kwargs()
        if sys.platform == "win32":
            self.assertEqual(options["creationflags"] & subprocess.CREATE_NO_WINDOW, subprocess.CREATE_NO_WINDOW)
            self.assertEqual(options["startupinfo"].wShowWindow, subprocess.SW_HIDE)

    def test_hidden_runner_never_uses_shell(self):
        completed = subprocess.CompletedProcess(["tool"], 0, "", "")
        with mock.patch("app_logging.subprocess.run", return_value=completed) as run:
            app_logging.run_hidden(["tool", "--version"], text=True)
        self.assertIs(run.call_args.kwargs["shell"], False)
    def test_progress_parser(self):
        value = YouTubeDownloader.__new__(YouTubeDownloader)._progress("305|1000|NA|50.2|14| 30.5%")
        self.assertEqual(value["percent"], 30.5); self.assertEqual(value["total_bytes"], 1000)
    def test_progress_parser_uses_estimate_and_missing_fields(self):
        value = YouTubeDownloader.__new__(YouTubeDownloader)._progress("1048576|NA|10485760|NA|NA|10.0%")
        self.assertEqual(value["total_bytes"],10485760); self.assertIsNone(value["speed"])
    def test_machine_events_and_exit_zero_complete_without_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            final=Path(tmp)/"مثال عربي file.mp4"; final.touch()
            process=mock.Mock(); process.stdout=iter([f"YD_FILE|{final}\r\n"]); process.wait.return_value=0; process.pid=42
            engine=YouTubeDownloader.__new__(YouTubeDownloader); engine._cancel_requested=False; engine.log=mock.Mock(); engine._process=None
            events=[]
            with mock.patch("downloader.popen_hidden",return_value=process):
                result=engine._download_process(["yt-dlp"],"https://youtu.be/abcdefghijk",Path(tmp),DownloadFormat.MP4,events.append)
            self.assertEqual(Path(result),final.resolve()); self.assertEqual(events[-1]["percent"],100.0)
    def test_two_stream_progress_and_postprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            final=Path(tmp)/"Example.mp4"; final.touch()
            lines=["YD_PROGRESS|1048576|10485760|NA|524288|18|10.0%\n","YD_PROGRESS|5242880|10485760|NA|1048576|5|50.0%\r\n","YD_POST|started\n",f"YD_FILE|{final}\n"]
            process=mock.Mock(); process.stdout=iter(lines); process.wait.return_value=0; process.pid=43
            engine=YouTubeDownloader.__new__(YouTubeDownloader); engine._cancel_requested=False; engine.log=mock.Mock(); events=[]
            with mock.patch("downloader.popen_hidden",return_value=process): engine._download_process(["yt-dlp"],"https://youtu.be/abcdefghijk",Path(tmp),DownloadFormat.MP4,events.append)
            self.assertEqual(events[0]["percent"],10.0); self.assertEqual(events[1]["percent"],50.0); self.assertIn("Merging",events[2]["message"]); self.assertEqual(events[-1]["percent"],100.0)
    def test_nonzero_exit_is_error(self):
        process=mock.Mock(); process.stdout=iter(["ERROR: failed\n"]); process.wait.return_value=1; process.pid=44
        engine=YouTubeDownloader.__new__(YouTubeDownloader); engine._cancel_requested=False; engine.log=mock.Mock()
        with mock.patch("downloader.popen_hidden",return_value=process), self.assertRaises(RuntimeError):
            engine._download_process(["yt-dlp"],"https://youtu.be/abcdefghijk",Path("."),DownloadFormat.MP4,None)
    def test_paths_with_spaces_and_resume_flags(self):
        engine = YouTubeDownloader.__new__(YouTubeDownloader)
        engine.runtime=mock.Mock(); engine.runtime.command.return_value=["C:\\Program Files\\yt-dlp.exe"]; engine.runtime.version.return_value="test"
        engine.log=mock.Mock(); engine._cancel_requested=False; engine._process=None
        with mock.patch.object(utils,"check_ffmpeg",return_value=(True,"")), mock.patch.object(engine,"_download_process",return_value="done") as run:
            engine.download("https://youtu.be/abcdefghijk",Path("C:/folder with spaces"),DownloadFormat.MP4)
        command=run.call_args.args[0]
        self.assertIn("C:\\Program Files\\yt-dlp.exe",command); self.assertIn("--continue",command); self.assertIn("--part",command)
    def test_cancel_terminates_process(self):
        engine=YouTubeDownloader.__new__(YouTubeDownloader); engine._cancel_requested=False
        process=mock.Mock(); process.poll.return_value=None; engine._process=process
        with mock.patch.object(sys,"platform","linux"):
            engine.request_cancel()
        process.terminate.assert_called_once()
    def test_updater_failure_preserves_runtime(self):
        runtime=DownloaderRuntime()
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source.exe"; source.touch(); runtime.command=lambda: [str(source)]
            with mock.patch.object(config,"DOWNLOADER_RUNTIME_DIR",Path(tmp)/"user"), mock.patch("subprocess.run",side_effect=OSError("offline")):
                ok,message=runtime.update()
        self.assertFalse(ok); self.assertIn("unchanged",message)
    def test_frozen_runtime_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/config.YTDLP_EXE_NAME; exe.touch(); runtime=DownloaderRuntime()
            with mock.patch.object(config,"DOWNLOADER_RUNTIME_DIR",Path(tmp)):
                self.assertEqual(runtime.command(),[str(exe)])
    def test_missing_ffmpeg(self):
        engine=YouTubeDownloader.__new__(YouTubeDownloader); engine.reset_cancel=lambda:None; engine.log=mock.Mock()
        with mock.patch.object(utils,"check_ffmpeg",return_value=(False,"FFmpeg missing")):
            with self.assertRaisesRegex(RuntimeError,"FFmpeg missing"): engine.download("https://youtu.be/abcdefghijk",Path("x"),DownloadFormat.MP3)

if __name__ == "__main__": unittest.main()
