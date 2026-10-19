#!/usr/bin/env python3
"""Fail closed on empty/black/static Minecraft CI recordings."""
import argparse
import json
import subprocess
import sys

def run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()

def validate(path, min_duration=5):
    info=json.loads(run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height",
                         "-of","json",path]))
    duration=float(info["format"]["duration"])
    streams=[s for s in info.get("streams",[]) if s.get("codec_type")=="video"]
    if duration<min_duration or not streams:
        raise ValueError("Video is missing or too short")
    # Crop 16 frames across the recording and sample tiny RGB thumbnails.
    # Raw pixels are evaluated only to reject uniform, empty, or frozen content.
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",path,"-vf",
        "fps=1/2,scale=32:18,format=gray","-frames:v","16","-f","rawvideo","-"])
    frame_size=32*18
    frames=[raw[i:i+frame_size] for i in range(0,len(raw),frame_size) if len(raw[i:i+frame_size])==frame_size]
    if len(frames)<3: raise ValueError("Insufficient decoded frames to inspect")
    if max(max(f)-min(f) for f in frames)<15:
        raise ValueError("Capture appears near-uniform; may be blank display")
    changes=[sum(abs(a-b) for a,b in zip(x,y))/frame_size for x,y in zip(frames,frames[1:])]
    if max(changes)<1.0:
        raise ValueError("Capture appears static; no meaningful motion verified")
    print(json.dumps({"valid_capture":True,"duration_seconds":duration,
        "sampled_frames":len(frames),"max_mean_frame_change":round(max(changes),2)}))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("video")
    args=parser.parse_args()
    try: validate(args.video)
    except (ValueError,KeyError,subprocess.CalledProcessError) as exc:
        print("INVALID GAMEPLAY VIDEO:",exc,file=sys.stderr);sys.exit(1)
