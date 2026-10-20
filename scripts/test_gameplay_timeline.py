#!/usr/bin/env python3
"""Regress grounded timestamp extraction from RCON output."""
import unittest
from extract_gameplay_decisions import extract

class TimelineTest(unittest.TestCase):
    def test_monotonic_video_alignment(self):
        transcript = (
            "HB_EVENT_TIME monotonic_ns=13000000000 command=sable auto-research-on\n"
            "sable auto-research-on => AUTO_RESEARCH ENABLED\n"
            "HB_EVENT_TIME monotonic_ns=15000000000 command=sable hypothesis-mill-inspect\n"
            "sable hypothesis-mill-inspect => HYPOTHESIS PROPOSED\n")
        events=extract(transcript, 10000000000)["events"]
        self.assertEqual([x["event"] for x in events],
            ["research_enabled","hypothesis_proposed"])
        self.assertEqual([x["approx_video_seconds"] for x in events],[3,5])
    def test_no_timestamp_is_not_invented(self):
        events=extract("HYPOTHESIS CONFIRMED",100)["events"]
        self.assertIsNone(events[0]["monotonic_ns"])
        self.assertNotIn("approx_video_seconds",events[0])

if __name__=="__main__":
    unittest.main()
