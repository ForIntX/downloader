import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class InstallerTests(unittest.TestCase):
    def test_shell_scripts_parse(self):
        for script in ("start.sh", "install.sh", "uninstall.sh"):
            result = subprocess.run(["sh", "-n", str(ROOT / script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_supported_package_managers_are_present(self):
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("apt-get install", text)
        self.assertIn("dnf install", text)
        self.assertIn("pacman -S", text)
        self.assertIn("gstreamer1.0-libav", text)
        self.assertIn("gstreamer1-plugin-libav", text)
        self.assertIn("gst-libav", text)
        self.assertIn("--check", text)

    def test_desktop_launcher_template(self):
        text = (ROOT / "assets/com.forintx.VideoIndirici.desktop").read_text(encoding="utf-8")
        self.assertIn("Type=Application", text)
        self.assertIn("Exec=downloader", text)
        self.assertIn("Icon=com.forintx.VideoIndirici", text)
        self.assertIn("Terminal=false", text)

    def test_distro_detection_dry_runs(self):
        cases = {
            "ubuntu": "apt-get install",
            "fedora": "dnf install",
            "arch": "pacman -S",
        }
        for distro, expected in cases.items():
            with self.subTest(distro=distro), tempfile.TemporaryDirectory() as directory:
                os_release = Path(directory) / "os-release"
                os_release.write_text(f'ID="{distro}"\n', encoding="utf-8")
                environment = {
                    **os.environ,
                    "VIDEO_INDIRICI_OS_RELEASE": str(os_release),
                    "VIDEO_INDIRICI_TEST_MISSING": " ffmpeg",
                }
                result = subprocess.run(
                    ["sh", str(ROOT / "install.sh"), "--check"],
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stdout)


if __name__ == "__main__":
    unittest.main()
