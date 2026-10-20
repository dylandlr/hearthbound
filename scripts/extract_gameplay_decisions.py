#!/usr/bin/env python3
"""Create a factual sidecar event timeline from real CI scenario RCON transcript.

No invented policy scores or inferred private reasoning. Events have transcript
line numbers, not video timestamps: synchronization awaits monotonic event clock.
"""
import argparse,json,pathlib,re
PATTERNS=[
 ("research_enabled",r"AUTO_RESEARCH ENABLED"),
 ("hypothesis_proposed",r"HYPOTHESIS PROPOSED"),
 ("haul_complete",r"Haul complete"),
 ("flour_observed",r"flour=([1-9][0-9]*)"),
 ("hypothesis_confirmed",r"HYPOTHESIS CONFIRMED"),
 ("research_credit",r"RESEARCH_CREDIT_GRANTED"),
]
def extract(text, capture_start_ns=None):
    events=[]
    seen=set()
    pending_ns=None
    for line_no,line in enumerate(text.splitlines(),1):
        stamp=re.search(r"HB_EVENT_TIME monotonic_ns=([0-9]+)",line)
        if stamp:
            pending_ns=int(stamp.group(1))
            continue
        for name,pattern in PATTERNS:
            if name not in seen and re.search(pattern,line,re.I):
                seen.add(name)
                event={"event":name,"transcript_line":line_no,
                       "evidence":line[:350],"monotonic_ns":pending_ns}
                if pending_ns is not None and capture_start_ns is not None:
                    event["approx_video_seconds"]=round((pending_ns-capture_start_ns)/1e9,3)
                events.append(event)
    return {"schema_version":1,"source":"RCON scenario transcript",
            "time_alignment":"Approximate elapsed time from FFmpeg launch request; includes capture startup delay",
            "events":events}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--scenario-log",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--capture-start-ns",type=int)
    a=p.parse_args()
    result=extract(pathlib.Path(a.scenario_log).read_text(errors="replace"),a.capture_start_ns)
    path=pathlib.Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"recorded_events":len(result["events"]),"names":[x["event"] for x in result["events"]]}))
