#!/usr/bin/env python3
"""Summarize roof mesh-hook evidence from the real Forge client log."""
import json
import pathlib
import re
import sys

log = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
pattern = re.compile(
    r"HEARTHBOUND_ROOF_STATE requested=(true|false) "
    r"candidateBlocks=(\\d+) previouslyHidden=(\\d+) "
    r"meshHookCalls=(\\d+) suppressedMeshCalls=(\\d+)"
)
events = [
    dict(requested=m[0] == "true", candidates=int(m[1]),
         previous=int(m[2]), hook_calls=int(m[3]), suppressed=int(m[4]))
    for m in pattern.findall(log.read_text(errors="replace"))
]
cutaway_events = [e for e in events if e["requested"] and e["candidates"] > 0]
status = ("NO_ACTIVE_CUTAWAY" if not cutaway_events else
          "NO_RENDER_HOOK_CALLS" if max(e["hook_calls"] for e in events) == 0 else
          "NO_SUPPRESSED_BLOCKS" if max(e["suppressed"] for e in events) == 0 else
          "SUPPRESSION_OBSERVED")
report = {"status": status, "events": events,
          "note": "Suppression observed alone does not prove visible geometry was removed."}
output.write_text(json.dumps(report, indent=2) + "\\n")
print(json.dumps(report))
