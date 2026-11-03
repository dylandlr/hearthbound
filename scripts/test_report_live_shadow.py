#!/usr/bin/env python3
"""Synthetic parser verification; not itself evidence of Minecraft production."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("report_live_shadow.py")
spec=importlib.util.spec_from_file_location("report_live_shadow",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def output(mode,action,experience):
    return (f"POLICY_PROBE policy=scripted_reference action={action} "
            f"citizen=123e4567-e89b-12d3-a456-426614174000 "
            f"pos=BlockPos{{x=9, y=100, z=3}} powered=true wheat=0 flour=1 "
            f"blocked=false experience={experience} mlp_action={action} "
            f"model=mill-mlp-v1 shadow_mode={mode} selected_action={action} "
            "model_disagreement=false action_masked=false EXECUTION_DISABLED")
def fixture():
    rows=[]
    for stage,expected in module.REQUIRED.items():
        experience=1 if stage=="citizen_experienced" else 0
        rows.append(f"LIVE_SHADOW_PAIR stage={stage} expected={expected} "
                    f"scripted={output('SCRIPTED',expected,experience)} "
                    f"trained={output('TRAINED_MLP',expected,experience)}")
    return "\n".join(rows)
def main():
    valid=fixture()
    result=module.analyze(valid)
    assert len(result["stages"])==3 and not result["learning_improvement_demonstrated"]
    for content in (
        valid.replace("shadow_mode=TRAINED_MLP","shadow_mode=SCRIPTED"),
        valid.replace("EXECUTION_DISABLED","EXECUTION_ENABLED"),
        valid.replace("citizen_experienced", "other_experiment"),
        valid+"\n"+valid.splitlines()[0],
        valid.replace("experience=1","experience=0"),
    ):
        try: module.analyze(content)
        except ValueError: pass
        else: raise AssertionError("Invalid evidence accepted")
    print("PASS 6 shadow report audit checks")
if __name__=="__main__":main()
