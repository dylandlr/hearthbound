#!/usr/bin/env python3
"""Render optional honest annotations over a separate copy of real Minecraft footage.

The original MP4 is never modified. Display intervals derive from measured RCON
observation timestamps, not imagined agent cognition or hand-written scene timing.
"""
import argparse
import json
from pathlib import Path
import subprocess

LABELS = {
    "research_enabled": "Autonomous research enabled",
    "hypothesis_proposed": "Hypothesis proposed - wheat milling",
    "haul_complete": "Hauling completed",
    "flour_observed": "Flour observed (not yet verified)",
    "research_credit": "Create processing callback VERIFIED",
    "hypothesis_confirmed": "Recipe knowledge confirmed",
}

def create_filter(events, duration):
    # The latest observed milestone remains visible until the next one; closely
    # spaced milestones may be too short to read, but their event data persists.
    valid = []
    for event in events:
        t = event.get("approx_video_seconds")
        if event.get("event") in LABELS and isinstance(t, (int, float)) and 0 <= t < duration:
            valid.append((float(t), event["event"]))
    valid.sort()
    # Minimum readable intervals, even when RCON milestones share one tick.
    # Preserve order, but shift the display of later events forward.
    readable=[]
    for observed, name in valid:
        start=max(observed, readable[-1][0]+1.4) if readable else observed
        if start < duration:
            readable.append((start, name))
    valid=readable
    filters = []
    for i, (start, name) in enumerate(valid):
        end = valid[i + 1][0] if i + 1 < len(valid) else duration
        if end <= start:
            continue
        text = LABELS[name]
        interval = f"between(t\\,{start:.3f}\\,{end:.3f})"
        filters.append(
            "drawbox=x=20:y=20:w=660:h=55:color=black@0.70:t=fill:enable='" + interval + "',"
            "drawtext=fontcolor=white:fontsize=23:x=38:y=36:"
            "text='" + text + "':enable='" + interval + "'"
        )
    if not filters:
        raise ValueError("No timestamped research events inside video duration")
    return ",".join(filters)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--events",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    data=json.loads(Path(a.events).read_text())
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=noprint_wrappers=1:nokey=1",a.video],
                         capture_output=True,text=True,check=True)
    duration=float(probe.stdout.strip())
    filters=create_filter(data["events"],duration)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",a.video,
                    "-vf",filters,"-c:v","libx264","-preset","veryfast","-crf","25",
                    "-pix_fmt","yuv420p","-an",a.output],check=True)
    print(f"Annotated {duration:.2f}s of genuine gameplay with timestamped RCON events")

if __name__=="__main__":
    main()
