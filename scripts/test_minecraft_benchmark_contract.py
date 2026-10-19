#!/usr/bin/env python3
"""Contract regression for benchmark aggregation; standard-library only."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT=pathlib.Path(__file__).with_name("aggregate_minecraft_simulations.py")
class BenchmarkContract(unittest.TestCase):
    def test_missing_seed_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            (root/"seed-11").mkdir()
            (root/"seed-11"/"summary.json").write_text(json.dumps(
                {"passed":True,"seed":11,"events":{},"measurements":{"ticks_to_confirmation":200}}))
            run=subprocess.run([sys.executable,str(SCRIPT),str(root),
                "--expected-trials","3","--output",str(root/"aggregate.json")],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertFalse((root/"aggregate.json").exists())
    def test_game_ticks_are_aggregated_without_fabricating_missing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for seed,ticks,passed in ((11,100,True),(42,200,True),(73,None,False)):
                d=root/str(seed);d.mkdir()
                measurements={"ticks_to_confirmation":ticks} if ticks is not None else None
                (d/"summary.json").write_text(json.dumps(
                    {"seed":seed,"passed":passed,"events":{},"measurements":measurements}))
            output=root/"aggregate.json"
            run=subprocess.run([sys.executable,str(SCRIPT),str(root),
                "--expected-trials","3","--output",str(output)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads(output.read_text())
            self.assertEqual(report["trials"],3)
            self.assertEqual(report["failed"],1)
            self.assertEqual(report["mean_milestone_ticks"]["ticks_to_confirmation"],150)
if __name__=="__main__":unittest.main()
