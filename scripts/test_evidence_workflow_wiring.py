#!/usr/bin/env python3
"""Static CI guard: reward exporter receives exactly its documented inputs."""
from pathlib import Path

def main():
    script=Path(".github/workflows/dedicated-server-smoke.yml").read_text()
    expected=("          python3 scripts/build_minecraft_experience.py \\\n"
              "            policy-trial-result.json live-shadow-report.json \\\n"
              "            --restart-log verified-restart.log --output minecraft-experience.json")
    if script.count(expected)!=1:
        raise AssertionError("Reward export CLI has broken continuation or extra arguments")
    for artifact in ("policy-rejection.json","source-observations.json",
                     "minecraft-experience.json"):
        if f"            {artifact}\n" not in script:
            raise AssertionError("Missing dedicated-server evidence artifact: "+artifact)
    if script.count("python3 scripts/report_source_observations.py")!=1:
        raise AssertionError("Missing or duplicated source observation collector")
    if script.count("python3 scripts/report_policy_rejection.py")!=1:
        raise AssertionError("Missing or duplicated shortage evidence collector")
    print("PASS 6 real-game evidence workflow wiring checks")

if __name__=="__main__":main()
