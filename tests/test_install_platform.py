import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("artcraft_install", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PlatformInstallTests(unittest.TestCase):
    def test_windows_installs_windows_marketplace_and_setup(self):
        commands = installer.plan("win32", "python", "codex", ROOT)
        self.assertEqual(Path(commands[0][1]), ROOT / "windows/scripts/setup.py")
        self.assertEqual(Path(commands[1][-1]), ROOT / "windows")
        self.assertEqual(commands[2][-1], "artcraft-agent@artcraft-windows")

    def test_macos_installs_current_plugin_and_setup(self):
        commands = installer.plan("darwin", "python3", "codex", ROOT)
        self.assertEqual(Path(commands[0][1]), ROOT / "scripts/setup.py")
        self.assertEqual(Path(commands[1][-1]), ROOT)
        self.assertEqual(commands[2][-1], "artcraft@artcraft-local")

    def test_unsupported_platform_cannot_install_macos_by_default(self):
        with self.assertRaises(ValueError):
            installer.plan("linux", "python3", "codex", ROOT)


if __name__ == "__main__":
    unittest.main()
