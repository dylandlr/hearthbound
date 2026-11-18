"""Inference-only action alias intervention; preserves the v0.4 environment.

An idle actor's current-site fresh INSPECT is a one-tick no-op with the same
actor-visible/physical result as WAIT. Pruning removes that duplicate action;
WAIT remains available and no productive action is forced. Evaluator inspection
counters and action-event logs can distinguish the aliases and are not inputs.
"""
import math

from colony_task_env import ACTIONS, mask as original_mask


def is_current_inspection(observation, action):
    """Recognize a legal current-position inspection from published features only."""
    admitted = original_mask(observation)
    if type(action) is not int or not 1 <= action <= 4 or not admitted[action]:
        return False
    offset = 6 + 8 * (action - 1)
    return (observation[offset + 6] == 1 and observation[offset + 3] == 1
            and observation[offset + 5] == 0)


def decision_mask(observation, prune=False):
    """Return the original mask, optionally removing only fresh local INSPECT aliases."""
    if type(prune) is not bool:
        raise ValueError("prune must be a boolean")
    admitted = list(original_mask(observation))
    if prune:
        for action in range(1, 5):
            if is_current_inspection(observation, action):
                admitted[action] = False
    return tuple(admitted)


def choose(model, observation, prune=False):
    """Rerank unchanged Q heads over the retained actions, with stable index ties."""
    admitted = decision_mask(observation, prune=prune)
    values = tuple(float(value) for value in model.values(observation))
    if len(values) != len(ACTIONS) or not all(math.isfinite(value) for value in values):
        raise ValueError("Invalid Q values")
    return max((index for index, allowed in enumerate(admitted) if allowed),
               key=lambda index: values[index])
