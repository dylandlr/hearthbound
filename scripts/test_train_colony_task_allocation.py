"""Learning implementation and trajectory accounting checks, not performance claims."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np

from colony_task_env import Env, mask
from train_colony_task_allocation import (
    Network, GAMMA, PERSONAL_WEIGHT, crossed_interval, evaluate, run_episode, stable_seed,
)


class TrainingTests(unittest.TestCase):
    def test_checkpoint_roundtrip_and_digest_validation(self):
        model = Network(7)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.json'
            model.save(path)
            loaded = Network.load(path)
            self.assertEqual(model.digest(), loaded.digest())
            data = json.loads(path.read_text())
            data['parameters']['b2'][0] += 1
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Network.load(path)

    def test_checkpoint_feature_order_is_part_of_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.json'
            Network(9).save(path)
            data = json.loads(path.read_text())
            data['features'][0], data['features'][1] = data['features'][1], data['features'][0]
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Network.load(path)

    def test_checkpoint_normalization_is_part_of_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.json'
            Network(9).save(path)
            data = json.loads(path.read_text())
            data['observation_contract']['hub_scale'] = 4
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Network.load(path)

    def test_reward_gradient_reduces_terminal_prediction_error(self):
        obs = Env(61).obs(0)
        online, target = Network(7), Network(11)
        original = online.digest()
        initial_error = abs(float(online.values(obs)[0]) - 1)
        item = dict(observation=obs, action=0, discounted_reward=1.,
                    next_observation=obs, duration=4, terminal=True)
        for _ in range(30):
            online.update([item] * 8, target)
        self.assertNotEqual(original, online.digest())
        self.assertLess(abs(float(online.values(obs)[0]) - 1), initial_error)
        self.assertEqual(online.updates, 30)

    def test_masked_future_values_cannot_change_bellman_target(self):
        obs = Env(63).obs(0)
        a = Network(14)
        b = copy.deepcopy(a)
        target_a = Network(15)
        target_b = copy.deepcopy(target_a)
        # All HAUL heads are invalid in this unknown-stock hub observation.
        self.assertFalse(any(mask(obs)[5:]))
        target_a.parameters['b2'][5:] = 1e9
        target_b.parameters['b2'][5:] = -1e9
        item = dict(observation=obs, action=0, discounted_reward=.1,
                    next_observation=obs, duration=3, terminal=False)
        a.update([item] * 8, target_a)
        b.update([item] * 8, target_b)
        self.assertEqual(a.digest(), b.digest())

    def test_evaluation_preserves_weights_and_optimizer_counts(self):
        model, initial = Network(17), Network(23)
        before = (model.digest(), initial.digest(), model.updates, initial.updates)
        rows, _ = evaluate(model, initial, [8000041, 8000042], 'standard', horizon=12)
        self.assertEqual(len(rows), 10)
        self.assertEqual(before, (model.digest(), initial.digest(), model.updates, initial.updates))
        self.assertTrue(all(r['conservation_residual_A'] == r['conservation_residual_B'] == 0
                            and r['tick'] == 12 for r in rows))

    def test_real_environment_experience_covers_each_tick_once(self):
        rng = random.Random(38)
        result, transitions = run_episode(
            lambda agent, obs: rng.choice([i for i, ok in enumerate(mask(obs)) if ok]),
            Env(71, horizon=24))
        for agent in range(2):
            own = [t for t in transitions if t['agent'] == agent]
            self.assertEqual(sum(t['duration'] for t in own), 24)
            self.assertEqual(sum(t['colony_reward'] for t in own), result['produced'])
            self.assertAlmostEqual(sum(t['personal_reward'] for t in own),
                                   result['personal_reward'][agent])
            self.assertEqual(sum(t['terminal'] for t in own), 1)

    def test_option_duration_discount_matches_independent_tick_example(self):
        class Timeline:
            agents, horizon, tick, done = 2, 4, 0, False
            events = []
            def ready(self):
                return {0: [0, 1], 1: [], 2: [1], 3: [0], 4: []}[self.tick]
            def obs(self, agent):
                values = list(Env(73, horizon=4).obs(agent))
                values[0] = (4 - self.tick) / 4
                return tuple(values)
            def step(self, actions):
                self.tick += 1
                self.done = self.tick == 4
                return {1: 0., 2: 4., 3: 0., 4: 8.}[self.tick], [-1., -2.], self.done
            def metrics(self):
                return dict(produced=12, conservation_residual_A=0, conservation_residual_B=0)
        result, transitions = run_episode(lambda agent, obs: 0, Timeline())
        own_a = [t for t in transitions if t['agent'] == 0]
        own_b = [t for t in transitions if t['agent'] == 1]
        self.assertEqual([t['duration'] for t in own_a], [3, 1])
        self.assertEqual([t['duration'] for t in own_b], [2, 2])
        self.assertAlmostEqual(own_a[0]['discounted_reward'],
                               4 * GAMMA - PERSONAL_WEIGHT * (1 + GAMMA + GAMMA ** 2))
        self.assertAlmostEqual(own_b[0]['discounted_reward'],
                               4 * GAMMA - 2 * PERSONAL_WEIGHT * (1 + GAMMA))
        self.assertEqual(result['colony_reward'], 12)

    def test_crossed_interval_and_seed_streams(self):
        self.assertEqual(crossed_interval([[2., 2.], [2., 2.]], repeats=40), [2., 2.])
        self.assertNotEqual(stable_seed('training-world', 17, 0), 9000000)
        self.assertNotEqual(stable_seed('training-world', 17, 0),
                            stable_seed('policy-exploration', 17))


if __name__ == '__main__':
    unittest.main(verbosity=2)
