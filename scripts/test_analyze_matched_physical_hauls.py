#!/usr/bin/env python3
"""Evidence-contract tests for small-sample physical Minecraft A/B aggregation."""
import copy
import unittest
from analyze_matched_physical_hauls import summarize

SHA="b"*64

def receipt(seed, scenario, policy, outcome):
    base={"schema":"hearthbound.matched-real-physical-haul.v1",
          "evidence_origin":"REAL_FORGE_WORLD_INVENTORY",
          "seed":seed,"scenario":scenario,"policy":policy,
          "model_sha256":SHA,
          "operator_triggered":True,
          "scout_distinct_from_executor":True,
          "training_includes_this_world":False,
          "no_model_updates":True,
          "research_reward_authorized":False,"technology_unlocked":False,
          "chest_counts_independently_read":True,
          "rewards_issued":False,"model_updated":False}
    if outcome=="ABSTAIN":
        return base | {"selected":"NONE","status":"ABSTAIN",
          "physical_success":False,"inventory_delta_verified":False,
          "before":{"A":3,"B":1,"destination":0},
          "after":{"A":3,"B":1,"destination":0},
          "utility":0.0,"completed_item_count":0}
    if outcome=="SUCCESS":
        return base | {"selected":"A","status":"EXECUTOR_COMPLETED",
          "job":"11111111-1111-4111-8111-111111111111",
          "physical_success":True,"inventory_delta_verified":True,
          "before":{"A":3,"B":1,"destination":0},
          "after":{"A":2,"B":1,"destination":1},
          "utility":1.0,"completed_item_count":1,
          "completion_receipt":"REPORT_HAUL_EXECUTION status=EXECUTOR_COMPLETED",
          "completed_server_ticks":100}
    if outcome=="FAIL":
        return base | {"selected":"A","status":"PAUSED_OR_QUARANTINED",
          "job":"11111111-1111-4111-8111-111111111111",
          "physical_success":False,"inventory_delta_verified":False,
          "before":{"A":0,"B":1,"destination":0},
          "after":{"A":0,"B":1,"destination":0},
          "utility":-0.5,"completed_item_count":0,
          "completed_server_ticks":20}
    raise ValueError("bad synthetic test mode")

class MatchedPhysicalEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.rows=[
            receipt(3101,"fresh","SCRIPTED","SUCCESS"),
            receipt(3101,"fresh","FROZEN_MLP","SUCCESS"),
            receipt(3102,"unannounced_depletion","SCRIPTED","FAIL"),
            receipt(3102,"unannounced_depletion","FROZEN_MLP","ABSTAIN")]
    def test_paired_summary(self):
        report=summarize(self.rows)
        self.assertEqual(report["paired_world_count"],2)
        self.assertEqual(report["physical_trial_count"],4)
        self.assertEqual(report["frozen_minus_scripted_mean_utility"],.25)
        self.assertTrue(report["sample_too_small_to_claim_superiority"])
        self.assertFalse(report["model_superiority_claimed"])
        self.assertEqual(report["policy"]["SCRIPTED"]["completed_items"],1)
        self.assertEqual(report["policy"]["FROZEN_MLP"]["abstain_rate"],.5)
    def test_reject_fabricated_completion(self):
        rows=copy.deepcopy(self.rows)
        rows[0]["after"]["destination"]=0
        with self.assertRaises(ValueError):summarize(rows)
    def test_reject_fabricated_utility(self):
        rows=copy.deepcopy(self.rows)
        rows[3]["utility"]=1.0
        with self.assertRaises(ValueError):summarize(rows)
    def test_reject_missing_arm(self):
        with self.assertRaises(ValueError):summarize(self.rows[:-1])
    def test_reject_wrong_model(self):
        rows=copy.deepcopy(self.rows)
        rows[3]["model_sha256"]="a"*64
        with self.assertRaises(ValueError):summarize(rows)
    def test_reject_duplicate_trial(self):
        with self.assertRaises(ValueError):summarize(self.rows+[self.rows[0]])
    def test_reject_reward_side_effect(self):
        rows=copy.deepcopy(self.rows)
        rows[0]["research_reward_authorized"]=True
        with self.assertRaises(ValueError):summarize(rows)
    def test_reject_imaginary_abstain_job(self):
        rows=copy.deepcopy(self.rows)
        rows[3]["job"]="fake"
        with self.assertRaises(ValueError):summarize(rows)

if __name__=="__main__":
    unittest.main()
