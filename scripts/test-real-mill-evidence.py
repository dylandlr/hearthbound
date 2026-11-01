#!/usr/bin/env python3
"""Synthetic parser tests only: do not count as real Minecraft gameplay."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location("mill", Path(__file__).with_name("verify-real-mill-production.py"))
mill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mill)
class EvidenceTests(unittest.TestCase):
    def test_no_evidence(self):
        self.assertFalse(mill.inspect("Sable spawned\nMILL NOT_CREATE_MILLSTONE")["production_verified"])
    def test_valid_pair(self):
        lines = ["HEARTHBOUND_PROCESS_CALLBACK pos=BlockPos{x=1, y=2, z=3} tick=200 wheat=1->0 flour=0->2",
                 "HEARTHBOUND_PROCESS_RECEIPT job=123e4567-e89b-12d3-a456-426614174000 citizen=123e4567-e89b-12d3-a456-426614174001"]
        self.assertTrue(mill.inspect("\n".join(lines))["production_verified"])
    def test_rejected_event(self):
        lines = ["HEARTHBOUND_PROCESS_CALLBACK pos=X tick=200 wheat=1->0 flour=0->1",
                 "HEARTHBOUND_PROCESS_REJECT invalid-transition",
                 "HEARTHBOUND_PROCESS_RECEIPT job=123e4567-e89b-12d3-a456-426614174000 citizen=123e4567-e89b-12d3-a456-426614174001"]
        self.assertFalse(mill.inspect("\n".join(lines))["production_verified"])
    def test_not_real_production(self):
        lines = ["HEARTHBOUND_PROCESS_CALLBACK pos=X tick=200 wheat=1->1 flour=0->1",
                 "HEARTHBOUND_PROCESS_RECEIPT job=123e4567-e89b-12d3-a456-426614174000 citizen=123e4567-e89b-12d3-a456-426614174001"]
        self.assertFalse(mill.inspect("\n".join(lines))["production_verified"])
if __name__ == "__main__":
    unittest.main()
