import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("dev_server", Path(__file__).with_name("dev_server.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DevServerTests(unittest.TestCase):
    def test_status_with_no_session_does_not_create_world(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(mod, "WORLD", root / "run"), patch.object(mod, "LOG", root / "run/logs/latest.log"), patch.object(mod, "STATE", root / "run/server.json"):
                mod.status()
                self.assertFalse((root / "run").exists())

    def test_start_requires_eula_before_running_gradle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(mod, "WORLD", root / "run"), patch.object(mod, "STATE", root / "run/server.json"), patch.object(mod, "ROOT", root), patch.object(mod.subprocess, "call") as called:
                with self.assertRaises(SystemExit):
                    mod.launch(False)
                called.assert_not_called()
                self.assertFalse((root / "run/eula.txt").exists())

    def test_explicit_eula_creates_persistent_online_mode_world(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(mod, "WORLD", root / "run"), patch.object(mod, "STATE", root / "run/server.json"), patch.object(mod, "ROOT", root), patch.object(mod.subprocess, "call", return_value=0) as called:
                self.assertEqual(mod.launch(True), 0)
                self.assertEqual((root / "run/eula.txt").read_text(), "eula=true\n")
                self.assertIn("online-mode=true", (root / "run/server.properties").read_text())
                self.assertFalse((root / "run/server.json").exists())
                called.assert_called_once()

if __name__ == "__main__":
    unittest.main()
