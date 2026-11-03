#!/usr/bin/env python3
"""Vision manifest: no image generation and no holdout leakage."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("vision_frame_manifest_contract.py")
s=importlib.util.spec_from_file_location("vision_contract",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
    status=m.manifest_contract()
    assert status["frames_recorded"]==status["models_trained"]==0
    assert status["status"]=="CONTRACT_ONLY_NO_FRAMES_COLLECTED"
    a=m.make_record("frame-a",12345,"mill-a",500,
                    [1.,70.,1.,45.,-5.],b"\x89PNG\r\n\x1a\nexample",320,180)
    b=m.make_record("frame-b",12345,"mill-a",501,
                    [1.,70.,1.,45.,-5.],b"\x89PNG\r\n\x1a\nanother",320,180)
    assert a["split"]==b["split"]
    assert a["rgb_sha256"]!=b["rgb_sha256"]
    assert m.validate(a) and m.validate(b)
    for variant in (
        dict(a,split="train" if a["split"]!="train" else "test"),
        dict(a,structured_labels_at_inference=True),
        dict(a,image_data_present=False),
        dict(a,tick=-1),
    ):
        try:m.validate(variant)
        except ValueError:pass
        else:raise AssertionError("Invalid vision metadata accepted")
    try:m.make_record("no-image",12345,"mill-a",502,[0]*5,b"",320,180)
    except ValueError:pass
    else:raise AssertionError("Empty image promoted as real frame")
    assert len(set(m.split_world(i,"mill-a") for i in range(50)))==3
    print("PASS RGB provenance, world-layout split isolation, label quarantine and honest uncollected data status")
if __name__=="__main__":main()
