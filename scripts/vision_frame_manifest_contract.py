#!/usr/bin/env python3
"""Minecraft machine-vision *metadata contract* only (NO frames captured).

A future Forge/client renderer can fill these records. This module validates
the frame/snapshot join and world-level split; it does not fake any images.
"""
import hashlib
import json
import math

SCHEMA="hearthbound.vision-frame-manifest.v1"
CHANNELS=("rgb_first_person","structured_training_label")

def split_world(world_seed,layout_id):
    if not isinstance(world_seed,int) or not isinstance(layout_id,str) or not layout_id:
        raise ValueError("World seed and layout identity required")
    key=f"{world_seed}|{layout_id}".encode()
    bucket=int.from_bytes(hashlib.sha256(key).digest()[:8],"big")%10
    return "train" if bucket<7 else "validation" if bucket<9 else "test"

def validate(record):
    if not isinstance(record,dict) or record.get("schema")!=SCHEMA:
        raise ValueError("Missing vision manifest schema")
    required=("frame_id","world_seed","layout_id","tick",
              "camera_pose","rgb_sha256","width","height","split")
    if any(k not in record for k in required):
        raise ValueError("Missing required frame provenance")
    if type(record["tick"]) is not int or record["tick"]<0:
        raise ValueError("Invalid server tick")
    if not isinstance(record["frame_id"],str) or not record["frame_id"]:
        raise ValueError("Invalid frame ID")
    if (type(record["width"]) is not int or type(record["height"]) is not int or
        not (64<=record["width"]<=4096 and 64<=record["height"]<=4096)):
        raise ValueError("Invalid dimensions")
    digest=record["rgb_sha256"]
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Missing verifiable RGB digest")
    pose=record["camera_pose"]
    if (not isinstance(pose,(list,tuple)) or len(pose)!=5 or
        any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in pose)):
        raise ValueError("Invalid camera coordinates/yaw/pitch")
    if record["split"]!=split_world(record["world_seed"],record["layout_id"]):
        raise ValueError("Train/validation/test split leaks world-layout identity")
    if record.get("visual_only_inference",True) and record.get("structured_labels_at_inference",False):
        raise ValueError("Visual-only inference cannot receive structured target labels")
    if record.get("image_data_present") is not True:
        raise ValueError("Metadata without real image bytes is NOT a captured frame")
    return True

def make_record(frame_id,world_seed,layout_id,tick,pose,rgb_bytes,width,height):
    if not isinstance(rgb_bytes,bytes) or len(rgb_bytes)==0:
        raise ValueError("Actual image bytes required, no synthetic frame claims")
    obj={
        "schema":SCHEMA,"frame_id":frame_id,"world_seed":world_seed,
        "layout_id":layout_id,"tick":tick,"camera_pose":pose,
        "rgb_sha256":hashlib.sha256(rgb_bytes).hexdigest(),
        "width":width,"height":height,
        "split":split_world(world_seed,layout_id),
        "image_data_present":True,"visual_only_inference":True,
        "structured_labels_at_inference":False,
    }
    validate(obj)
    return obj

def manifest_contract():
    return {
        "schema":SCHEMA,"status":"CONTRACT_ONLY_NO_FRAMES_COLLECTED",
        "frames_recorded":0,"models_trained":0,
        "required_capture_channels":list(CHANNELS),
        "required_alignment":"RGB and labels must use same authoritative server tick",
        "holdout_unit":"world_seed + layout_id, never adjacent frames",
        "vision_baselines":["CNN_from_scratch","pretrained_encoder_explicit_control",
                            "structured_only","visual_only","fusion"],
        "authority":"image prediction is untrusted hypothesis; server controls inventory/task execution",
    }
if __name__=="__main__":
    print(json.dumps(manifest_contract(),sort_keys=True))
