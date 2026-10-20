#!/usr/bin/env python3
"""Fast deterministic render test for video overlay; no Minecraft startup needed."""
import json, pathlib, subprocess, sys, tempfile
from annotate_gameplay_video import create_filter

events=[
 {"event":"research_enabled","approx_video_seconds":0.25},
 {"event":"flour_observed","approx_video_seconds":0.75},
 {"event":"research_credit","approx_video_seconds":1.3},
]
f=create_filter(events,6.0)
assert "Flour observed (not yet verified)" in f
assert "Create processing callback VERIFIED" in f
assert "between(t\\\\,0.250\\\\,1.650)" in f
assert "between(t\\\\,1.650\\\\,3.050)" in f
with tempfile.TemporaryDirectory() as tmp:
    p=pathlib.Path(tmp)
    video=p/"source.mp4"
    dest=p/"annotated.mp4"
    timeline=p/"events.json"
    timeline.write_text(json.dumps({"events":events}))
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","lavfi","-i","color=c=gray:s=320x180:r=15:d=6",
        "-c:v","libx264","-pix_fmt","yuv420p",str(video)],check=True)
    subprocess.run([sys.executable,"scripts/annotate_gameplay_video.py",
        "--video",str(video),"--events",str(timeline),"--output",str(dest)],check=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-xerror",
        "-i",str(dest),"-f","null","-"],check=True)
    assert dest.stat().st_size>1000
print("PASS: overlay renders and decodes on a synthetic CI fixture")
