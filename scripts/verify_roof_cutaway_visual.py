#!/usr/bin/env python3
"""Pixel-based roof cutaway evidence; report results without guessing success.

The test is deliberately strict: a live client must visibly change geometry
when toggling F8, and must return to the baseline after toggling it off.
"""
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops

folder=Path(sys.argv[1] if len(sys.argv)>1 else "gameplay-capture")
files=["player-cutaway-off.png","player-cutaway-on.png","player-cutaway-restored.png"]
images=[Image.open(folder/name).convert("RGB") for name in files]
if len({im.size for im in images})!=1:
    raise SystemExit("Cutaway screenshots have inconsistent dimensions")
width,height=images[0].size
# Ignore HUD overlays: inspect the middle 70% by 70% of the world view.
bounds=(int(width*.15),int(height*.15),int(width*.85),int(height*.85))
cropped=[image.crop(bounds) for image in images]
def pixel_difference(a,b,threshold=25):
    diff=ImageChops.difference(a,b)
    count=sum(1 for rgb in diff.getdata() if max(rgb)>threshold)
    return count/(a.width*a.height)
changed=pixel_difference(cropped[0],cropped[1])
restored=pixel_difference(cropped[0],cropped[2])
report={"schema":"hearthbound.cutaway-visual.v1",
        "capture_size":[width,height],"world_crop":list(bounds),
        "changed_fraction":round(changed,6),
        "restored_fraction":round(restored,6),
        "visually_changed":changed>0.01,
        "restored_close_to_baseline":restored<0.08,
        "disclaimer":"pixel comparison alone cannot prove correct roof removal"}
(folder/"roof-cutaway-visual-report.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
if not report["visually_changed"]:
    raise SystemExit("FAIL: roof cutaway did not visibly change world-view pixels")
if not report["restored_close_to_baseline"]:
    raise SystemExit("FAIL: roof did not return close to baseline")
