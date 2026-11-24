import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from courier_economy_env import ACTIONS, Env, mask
from train_courier_economy import (GAMMA, PERSONAL_WEIGHT, Network, evaluate,
                                  run_episode, summarize, train)


class LearnerTests(unittest.TestCase):
    def setUp(self):
        self.observation = Env(718, agents=2, horizon=12).obs(0)

    def test_double_dqn_masks_online_choice_and_uses_duration(self):
        online, target = Network(1), Network(2)
        for model in (online, target):
            for values in model.parameters.values():
                values.fill(0.)
        valid = np.flatnonzero(mask(self.observation))
        self.assertGreater(len(valid), 1)
        chosen, other = valid[:2]
        online.parameters["b2"][chosen] = 10
        target.parameters["b2"][chosen] = 3
        target.parameters["b2"][other] = 100
        invalid = np.flatnonzero(~np.asarray(mask(self.observation)))
        if len(invalid):
            online.parameters["b2"][invalid[0]] = 10000
        transition = dict(next_observation=self.observation, terminal=False,
                          discounted_reward=1.25, duration=4)
        expected = online.bellman_targets([transition], target)
        self.assertAlmostEqual(expected[0], 1.25 + GAMMA ** 4 * 3)
        transition["terminal"] = True
        self.assertEqual(online.bellman_targets([transition], target)[0], 1.25)

    def test_huber_gradients_match_numerical_derivatives(self):
        model = Network(29, hidden=5)
        model.parameters["b1"].fill(.7)
        observations = np.asarray([self.observation, self.observation])
        actions = [0, 0]
        expected = model.values(observations)[:, 0] + np.asarray([.4, 2.])
        _, gradients = model.loss_and_gradients(observations, actions, expected)
        for name, index in [("w1", (0, 0)), ("w1", (1, 2)), ("b1", (0,)),
                            ("w2", (0, 0)), ("w2", (2, 0)), ("b2", (0,))]:
            value, epsilon = model.parameters[name][index], 1e-6
            model.parameters[name][index] = value + epsilon
            plus, _ = model.loss_and_gradients(observations, actions, expected)
            model.parameters[name][index] = value - epsilon
            minus, _ = model.loss_and_gradients(observations, actions, expected)
            model.parameters[name][index] = value
            self.assertAlmostEqual(gradients[name][index], (plus - minus) / (2 * epsilon), places=6)

    def test_update_is_finite_and_changes_weights(self):
        model, target = Network(3), Network(3)
        transition = dict(observation=self.observation, action=0,
            next_observation=self.observation, terminal=True, discounted_reward=2., duration=1)
        before = model.digest()
        loss = model.update([transition] * 4, target)
        self.assertTrue(np.isfinite(loss))
        self.assertNotEqual(before, model.digest())
        self.assertEqual(model.updates, 1)
        self.assertTrue(all(np.isfinite(p).all() for p in model.parameters.values()))

    def test_checkpoint_roundtrip_and_tampering(self):
        model = Network(10, hidden=7)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            model.save(path)
            loaded = Network.load(path)
            self.assertEqual(loaded.digest(), model.digest())
            np.testing.assert_array_equal(loaded.values(self.observation), model.values(self.observation))
            data = json.loads(path.read_text())
            data["parameters"]["b2"][0] += .001
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "digest"):
                Network.load(path)
            model.save(path)
            data = json.loads(path.read_text())
            data["observation_contract"]["features"] = ["omniscient_stock"]
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "contract"):
                Network.load(path)

    def test_each_actor_receives_every_tick_reward_while_busy(self):
        observation = self.observation

        class ThreeTickWorld:
            agents, horizon = 2, 3
            tick, done = 0, False
            events = []

            def ready(self):
                return [0, 1] if self.tick == 0 else [1]

            def obs(self, agent):
                return observation

            def step(self, actions):
                assert set(actions) == set(self.ready())
                reward = [0., 2., 0.][self.tick]
                self.tick += 1
                self.done = self.tick == self.horizon
                return reward, [-.1, -.2], self.done

            def metrics(self):
                return dict(produced=2, conservation_residual_A=0, conservation_residual_B=0)

        metrics, transitions = run_episode(lambda a, o: 0, ThreeTickWorld())
        first = next(t for t in transitions if t["agent"] == 0)
        self.assertEqual(first["duration"], 3)
        self.assertTrue(first["terminal"])
        self.assertAlmostEqual(first["discounted_reward"],
            -.1 * PERSONAL_WEIGHT + GAMMA * (2 - .1 * PERSONAL_WEIGHT)
            + GAMMA ** 2 * (-.1 * PERSONAL_WEIGHT))
        np.testing.assert_allclose(metrics["personal_reward"], [-.3, -.6])
        self.assertEqual(metrics["colony_reward"], 2)

    def test_real_training_and_frozen_evaluation(self):
        model, initial, stats = train(17, 8, agents=2, horizon=32)
        self.assertGreater(stats["optimizer_updates"], 0)
        self.assertNotEqual(model.digest(), initial.digest())
        before = (model.digest(), initial.digest(), model.updates)
        rows, _ = evaluate(model, initial, [9400901], agents=2, horizon=16)
        self.assertEqual(len(rows), 8)
        self.assertEqual([r for r in rows if r["status"] != "valid"], [])
        self.assertEqual(before, (model.digest(), initial.digest(), model.updates))
        self.assertTrue(all(r["conservation_residual_A"] == r["conservation_residual_B"] == 0 for r in rows))

    def test_evaluation_trials_have_distinct_scoped_identities(self):
        model = Network(31)
        first, examples = evaluate(model, copy.deepcopy(model), [9400902],
                                   agents=2, horizon=4, evaluation_scope="17")
        second, _ = evaluate(model, copy.deepcopy(model), [9400902],
                             agents=2, horizon=4, evaluation_scope="23")
        identities = [r["run_id"] for r in first + second]
        self.assertEqual(len(set(identities)), 16)
        self.assertTrue(all(r["status"] == "valid" for r in first + second))
        self.assertTrue(all(example["run_id"].startswith("eval:17:") for example in examples.values()))
        self.assertEqual([r["produced"] for r in first], [r["produced"] for r in second])

    def test_failure_retained_and_prevents_paired_imputation(self):
        rows = [dict(training_seed=17, world_seed=11, policy="trained", communication="local",
                     status="valid", produced=4),
                dict(training_seed=17, world_seed=11, policy="untrained", communication="local",
                     status="failed", error="test failure", produced=None)]
        result = summarize(rows, [17], [11])
        self.assertEqual(result["conditions"]["untrained:local"]["failed"], 1)
        comparison = result["paired_differences"]["local_trained_minus_untrained:local"]
        self.assertFalse(comparison["complete"])
        self.assertIsNone(comparison["mean_products_difference"])


if __name__ == "__main__":
    unittest.main()
