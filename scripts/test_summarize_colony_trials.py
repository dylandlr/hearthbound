import json
import tempfile
import unittest
from pathlib import Path
from summarize_colony_trials import classify, summarize, SEEDS

class ReliabilityTest(unittest.TestCase):
    def test_partial_poll_is_not_terminal_failure(self):
        self.assertEqual(classify('COLONY_V1 done=3',None),'UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE')
    def test_specific_failure_requires_terminal_physical_evidence(self):
        for physical,done,expected in [(True,3,'THREE_OF_FOUR_ACCOUNTING_FAILURE'),(False,3,'OTHER_TERMINAL_FAILURE'),(True,2,'OTHER_TERMINAL_FAILURE')]:
            log='HEARTHBOUND_TERMINAL_ACCOUNTING_V1 '+json.dumps(dict(done=done,destination_has_four_wheat=physical,deadline_exhausted=True))
            self.assertEqual(classify(log,None),expected)
    def test_missing_worlds_stay_in_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            summary=summarize(root)
            self.assertEqual(summary['planned_worlds'],3)
            self.assertEqual(summary['unclassified_worlds'],3)
            self.assertIsNone(summary['observed_failure_fraction'])
            self.assertEqual(summary['planned_failure_fraction_bounds'],[0,1])
            folder=root/'real-four-citizen-colony-evidence-0';folder.mkdir()
            (folder/'trial-metadata.json').write_text(json.dumps(dict(trial=0,seed=SEEDS[0],fresh_world=True,commit='a'*40,run_id='1',attempt='1')))
            (folder/'real-four-citizen-rcon.log').write_text('HEARTHBOUND_TERMINAL_ACCOUNTING_V1 '+json.dumps(dict(done=3,destination_has_four_wheat=True,deadline_exhausted=True)))
            summary=summarize(root)
            self.assertEqual(summary['three_of_four_failures'],1)
            self.assertEqual(summary['unclassified_worlds'],2)
            self.assertEqual(summary['planned_failure_fraction_bounds'],[1/3,1])
            self.assertLess(summary['wilson_95_observed_only'][0],1)
    def test_manifest_seed_swap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'real-four-citizen-colony-evidence-0';folder.mkdir()
            (folder/'trial-metadata.json').write_text(json.dumps(dict(trial=0,seed=SEEDS[1],fresh_world=True)))
            with self.assertRaises(ValueError): summarize(root)

if __name__=='__main__': unittest.main()
