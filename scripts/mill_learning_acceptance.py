"""Independent numeric oracle for live RCON shadow replay (no server control)."""
import math


def fields(response):
    return dict(token.split("=", 1) for token in response.split() if "=" in token)


def require_replay(response, proposal):
    actual, evidence = fields(response), fields(proposal)
    expected = {
        "status": "REPLAYED", "samples": "1", "updates": "1",
        "personal_milli": "500", "replay_from_zero": "true",
        "model_persisted": "false", "success_only": "true",
        "shadow_learning_authorized": "true", "policy_control": "false",
        "reward_authorized": "false", "learning_authorized": "false",
        "physical_evidence_id": evidence["physical_evidence_id"],
        "citizen": evidence["citizen"],
    }
    if not response.startswith("MILL_LEARNING_SHADOW ") or "NO_RESEARCH_CREDIT" not in response:
        raise AssertionError("Missing shadow learning boundary: " + response)
    for key, value in expected.items():
        if actual.get(key) != value:
            raise AssertionError(f"Incorrect {key}: {response}")
    duration = int(evidence["process_finish_tick"]) - int(evidence["assigned_tick"])
    if duration <= 0 or int(actual["duration_ticks"]) != duration:
        raise AssertionError("Duration not derived from executor and process receipt")
    event = f"hearthbound:mill:v1:{evidence['world']}:minecraft:overworld:{evidence['job']}"
    if actual.get("event") != event:
        raise AssertionError("Learning event is not the fixture's physical outcome")
    target = .5 * .999 ** duration
    for key, value in {"alpha": .25, "gamma_per_tick": .999,
                       "target": target, "q_before": 0.0, "q_after": .25 * target}.items():
        observed = float(actual[key])
        if not math.isfinite(observed) or not math.isclose(observed, value, rel_tol=1e-12, abs_tol=1e-15):
            raise AssertionError(f"Incorrect terminal value update {key}: {response}")
    if not 0 < float(actual["q_after"]) < target:
        raise AssertionError("No real numeric learning update occurred")


def require_denial(response, reason):
    actual = fields(response)
    if not response.startswith("MILL_LEARNING_SHADOW "):
        raise AssertionError("Missing learning denial: " + response)
    for key, value in {"status": "DENIED", "reason": reason, "updates": "0",
                       "shadow_learning_authorized": "false", "policy_control": "false",
                       "reward_authorized": "false", "learning_authorized": "false"}.items():
        if actual.get(key) != value:
            raise AssertionError(f"Invalid denial {key}: {response}")
    if any(key in actual for key in ("q_after", "target")):
        raise AssertionError("Denied evidence exposed a cached trained value")
