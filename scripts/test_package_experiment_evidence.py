import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "evidence", Path(__file__).with_name("package_experiment_evidence.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class EvidenceTests(unittest.TestCase):
    def test_missing_logs_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            data = module.make_manifest(Path(folder))
            self.assertFalse(data["verified_runtime"])
            self.assertFalse(data["gameplay_markers_observed"])
            self.assertFalse(data["restart_markers_observed"])

    def test_required_markers_still_need_successful_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "gametest.log").write_text("\n".join(module.MARKERS[:4] + (module.MARKERS[7], module.MARKERS[11])))
            (root / "server-smoke.log").write_text("\n".join(module.MARKERS[4:7] + module.MARKERS[8:]))
            old = os.environ.get("HB_JOB_STATUS")
            try:
                os.environ["HB_JOB_STATUS"] = "failure"
                data = module.make_manifest(root)
                self.assertTrue(data["gameplay_markers_observed"])
                self.assertTrue(data["restart_markers_observed"])
                self.assertFalse(data["verified_runtime"])
                os.environ["HB_JOB_STATUS"] = "success"
                self.assertTrue(module.make_manifest(root)["verified_runtime"])
            finally:
                if old is None:
                    os.environ.pop("HB_JOB_STATUS", None)
                else:
                    os.environ["HB_JOB_STATUS"] = old

    def test_sha256_is_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "gametest.log").write_text("abc")
            data = module.make_manifest(root)
            self.assertEqual(data["files"]["gametest.log"]["sha256"],
                             "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

if __name__ == "__main__":
    unittest.main()
