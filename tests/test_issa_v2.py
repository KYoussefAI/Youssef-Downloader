import unittest
from unittest import mock
import tempfile
from pathlib import Path
import config,utils
from downloader import YouTubeDownloader

class URLValidationTests(unittest.TestCase):
    def test_accepted(self):
        for link in ("https://www.youtube.com/watch?v=abcdefghijk","youtu.be/abcdefghijk","https://youtube.com/shorts/abcdefghijk","https://m.youtube.com/live/abcdefghijk"):
            with self.subTest(link=link):
                self.assertTrue(utils.validate_url(link)[0])
    def test_reject_impersonation_and_injection(self):
        for link in ("https://youtube.com.evil.org/watch?v=abcdefghijk","https://evil.org/?next=https://youtube.com/watch?v=abcdefghijk","javascript:alert(1)","https://youtube.com@evil.org/watch?v=abcdefghijk","https://youtube.com/playlist?list=ABC","https://youtube.com/watch?v=bad"):
            with self.subTest(link=link):
                self.assertFalse(utils.validate_url(link)[0])
    def test_certificates_are_checked(self):
        self.assertNotIn("--no-check-certificates",YouTubeDownloader._common())
    def test_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(utils,"SETTINGS_FILE",Path(folder)/"settings.json"):
                utils.save_settings("C:/My Downloads","mp3")
                self.assertEqual(utils.load_settings(),{"download_dir":"C:/My Downloads","format":"mp3"})

if __name__=="__main__": unittest.main()
