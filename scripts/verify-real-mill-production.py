#!/usr/bin/env python3
"""Fail-closed evidence audit for actual dedicated-server logs. Does not simulate Minecraft."""
import argparse
import json
import pathlib
import re
import sys

CALLBACK = re.compile(r"HEARTHBOUND_PROCESS_CALLBACK\s+pos=(.+?)\s+tick=(\d+)\s+wheat=(\d+)->(\d+)\s+flour=(\d+)->(\d+)")
RECEIPT = re.compile(r"HEARTHBOUND_PROCESS_RECEIPT\s+job=([0-9a-fA-F-]{36})\s+citizen=([0-9a-fA-F-]{36})")
REJECT = re.compile(r"HEARTHBOUND_PROCESS_(?:REJECT|VETO)")
CREDITS = re.compile(r"HEARTHBOUND_RESEARCH_CREDIT_COMMITTED\s+event=([^\s]+)\s+citizen=([^\s]+)")
def inspect(log):
    lines = log.splitlines()
    callbacks = []
    receipts = []
    for n, line in enumerate(lines, 1):
        m = CALLBACK.search(line)
        if m:
            pos, tick, wb, wa, fb, fa = m.groups()
            callbacks.append({"line": n, "pos": pos, "tick": int(tick), "wheat_before": int(wb),
                              "wheat_after": int(wa), "flour_before": int(fb), "flour_after": int(fa)})
        m = RECEIPT.search(line)
        if m:
            receipts.append({"line": n, "job": m.group(1), "citizen": m.group(2)})
    valid = [c for c in callbacks if c["wheat_before"] == 1 and c["wheat_after"] == 0
             and c["flour_before"] == 0 and c["flour_after"] > 0]
    # Proof must be from the same server log sequence, not fabricated report metrics.
    linked = [(c, r) for c in valid for r in receipts if c["line"] < r["line"] <= c["line"] + 25
              and not any(REJECT.search(lines[i]) for i in range(c["line"], r["line"] - 1))]
    return {"schema": "hearthbound.real-mill-evidence.v1",
            "callbacks": len(callbacks), "valid_physical_transitions": len(valid),
            "receipts": len(receipts), "linked_evidence": len(linked),
            "research_credit_markers": sum(bool(CREDITS.search(line)) for line in lines),
            "production_verified": bool(linked),
            "examples": [{"job": r["job"], "citizen": r["citizen"], "pos": c["pos"], "tick": c["tick"],
                          "flour_delta": c["flour_after"] - c["flour_before"]} for c, r in linked[:5]]}
def main():
    p = argparse.ArgumentParser()
    p.add_argument("server_log", type=pathlib.Path)
    p.add_argument("--require-research-credit", action="store_true")
    args = p.parse_args()
    report = inspect(args.server_log.read_text(encoding="utf-8", errors="replace"))
    print(json.dumps(report, indent=2))
    if not report["production_verified"]:
        print("FAIL: No real Create processing callback paired with a verified receipt", file=sys.stderr)
        return 1
    if args.require_research_credit and not report["research_credit_markers"]:
        print("FAIL: Production observed, but no committed research credit", file=sys.stderr)
        return 2
    return 0
if __name__ == "__main__":
    sys.exit(main())
