import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from recurrent_coordination_policy import GAMMA, GAE_LAMBDA, PERSONAL_WEIGHT, SETTINGS
from recurrent_coordination_policy import Network, collect_episode, generalized_advantages
from recurrent_coordination_policy import prepare_batch, train
from selective_communication_env import ACTIONS, CRITIC_FEATURES, Env, FEATURES, mask


class RecurrentPolicyTests(unittest.TestCase):
    def setUp(self):
        self.world = Env(81032, agents=4, horizon=32)
        self.observation = self.world.actor_obs(0)

    def actor_sequence(self, model):
        hidden, sequence = model.initial_hidden(), []
        for index, advantage in enumerate((.7, -.4, .2)):
            obs = list(self.observation)
            obs[0] -= index * .03
            probs, hidden = model.distribution(obs, hidden)
            legal = np.flatnonzero(mask(obs))
            action = int(legal[index % len(legal)])
            sequence.append(dict(observation=tuple(obs), mask=tuple(mask(obs)), action=action,
                old_log_probability=math.log(float(probs[action])), normalized_advantage=advantage))
        return sequence

    def finite_difference(self, model, loss_function, gradients, names, tolerance=2e-6):
        epsilon = 1e-5
        for name in names:
            tensor = model.parameters[name]
            indices = list(np.ndindex(tensor.shape))
            chosen = indices if len(indices) <= 10 else [indices[i] for i in np.linspace(0, len(indices)-1, 10, dtype=int)]
            for index in chosen:
                original = tensor[index]
                tensor[index] = original + epsilon
                plus = loss_function()
                tensor[index] = original - epsilon
                minus = loss_function()
                tensor[index] = original
                numerical = (plus - minus) / (2 * epsilon)
                self.assertAlmostEqual(numerical, gradients[name][index], delta=tolerance,
                    msg=f"{name}{index}: numerical {numerical}, analytic {gradients[name][index]}")

    def test_recurrent_bptt_clipped_policy_and_entropy_gradients(self):
        model = Network(12, hidden=3, critic_hidden=3)
        sequences = [self.actor_sequence(model)]
        _, gradients, _ = model.actor_loss_and_gradients(sequences)
        self.finite_difference(model, lambda: model.actor_loss_and_gradients(sequences)[0],
            gradients, [k for k in model.parameters if k.startswith("actor_")])
        self.assertGreater(np.linalg.norm(gradients["actor_wh"]), 0)

    def test_feedforward_policy_gradients_and_no_recurrent_tensor(self):
        model = Network(12, recurrent=False, hidden=3, critic_hidden=3)
        sequences = [self.actor_sequence(model)]
        _, gradients, _ = model.actor_loss_and_gradients(sequences)
        self.assertNotIn("actor_wh", model.parameters)
        self.finite_difference(model, lambda: model.actor_loss_and_gradients(sequences)[0],
            gradients, [k for k in model.parameters if k.startswith("actor_")])

    def test_ppo_clipping_zeroes_only_the_correct_objective_branch(self):
        model = Network(12, recurrent=False, hidden=3)
        item = self.actor_sequence(model)[0]
        for advantage, ratio in ((1., 1.5), (-1., .5)):
            blocked = copy.deepcopy(item)
            blocked["normalized_advantage"] = advantage
            blocked["old_log_probability"] -= math.log(ratio)
            _, gradients, statistics = model.actor_loss_and_gradients([[blocked]], entropy_coefficient=0.)
            self.assertEqual(statistics["clip_fraction"], 1.)
            self.assertTrue(all(np.count_nonzero(g) == 0 for g in gradients.values()))
        for advantage, ratio in ((1., .5), (-1., 1.5)):
            allowed = copy.deepcopy(item)
            allowed["normalized_advantage"] = advantage
            allowed["old_log_probability"] -= math.log(ratio)
            _, gradients, _ = model.actor_loss_and_gradients([[allowed]], entropy_coefficient=0.)
            self.assertGreater(np.linalg.norm(gradients["actor_bo"]), 0.)

    def test_centralized_critic_gradients(self):
        model = Network(16, hidden=3, critic_hidden=3)
        inputs = [self.world.critic_state(i) for i in range(4)]
        targets = np.array([.2, -.1, 1.5, .7])
        _, gradients = model.critic_loss_and_gradients(inputs, targets)
        self.finite_difference(model, lambda: model.critic_loss_and_gradients(inputs, targets)[0],
            gradients, [k for k in model.parameters if k.startswith("critic_")])

    def test_duration_correct_gae_and_terminal_no_bootstrap(self):
        sequence = [dict(duration=3, discounted_reward=1., value=.5, terminal=False),
                    dict(duration=2, discounted_reward=2., value=.7, terminal=True)]
        generalized_advantages(sequence)
        expected_last = 2. - .7
        expected_first = 1. + GAMMA ** 3 * .7 - .5 + (GAMMA * GAE_LAMBDA) ** 3 * expected_last
        self.assertAlmostEqual(sequence[1]["advantage"], expected_last)
        self.assertAlmostEqual(sequence[0]["advantage"], expected_first)
        self.assertAlmostEqual(sequence[1]["return"], 2.)
        self.assertAlmostEqual(sequence[0]["return"], expected_first + .5)
        for invalid in ([dict(duration=0, discounted_reward=1., value=0., terminal=True)],
                        [dict(duration=1, discounted_reward=1., value=0., terminal=False)]):
            with self.assertRaises(ValueError):
                generalized_advantages(invalid)

    def test_hidden_states_are_external_and_feedforward_ignores_history(self):
        recurrent = Network(21)
        feedforward = Network(21, recurrent=False)
        for name in feedforward.parameters:
            np.testing.assert_array_equal(recurrent.parameters[name], feedforward.parameters[name])
        h0, h1 = recurrent.initial_hidden(), np.ones(recurrent.hidden) * .4
        before = h1.copy()
        p0, _ = recurrent.distribution(self.observation, h0)
        p1, _ = recurrent.distribution(self.observation, h1)
        self.assertGreater(np.linalg.norm(p0-p1), 1e-6)
        np.testing.assert_array_equal(h1, before)
        np.testing.assert_array_equal(feedforward.distribution(self.observation, h0)[0],
                                      feedforward.distribution(self.observation, h1)[0])
        self.assertFalse(np.shares_memory(recurrent.initial_hidden(), recurrent.initial_hidden()))

    def test_actor_has_no_centralized_critic_dependency_and_masks_are_exact(self):
        model = Network(22)
        probs, hidden = model.distribution(self.observation, model.initial_hidden())
        for name in model.parameters:
            if name.startswith("critic_"):
                model.parameters[name].fill(100.)
        later, _ = model.distribution(self.observation, model.initial_hidden())
        np.testing.assert_array_equal(probs, later)
        self.assertAlmostEqual(float(probs.sum()), 1., places=14)
        self.assertTrue(all(p == 0 for p, valid in zip(probs, mask(self.observation)) if not valid))
        rng = np.random.default_rng(188)
        for _ in range(40):
            action, _, logp = model.act(self.observation, hidden, rng)
            self.assertTrue(mask(self.observation)[action])
            self.assertTrue(math.isfinite(logp))
        with self.assertRaises(ValueError):
            model.act(self.observation, hidden)

    def test_rollout_continuously_credits_busy_actor_ticks_and_resets_world_memory(self):
        model = Network(23)
        rng = np.random.default_rng(19)
        metrics, sequences = collect_episode(model, self.world, rng, trace=True)
        self.assertEqual(len(sequences), self.world.agents)
        self.assertTrue(any(t["duration"] > 1 for sequence in sequences for t in sequence))
        for agent, sequence in enumerate(sequences):
            self.assertEqual(sum(t["duration"] for t in sequence), self.world.horizon)
            self.assertTrue(sequence[-1]["terminal"])
            self.assertFalse(any(t["terminal"] for t in sequence[:-1]))
            self.assertAlmostEqual(sum(t["personal_reward"] for t in sequence), metrics["personal_reward"][agent])
            self.assertEqual(sum(t["colony_reward"] for t in sequence), metrics["produced"])
            first = next(row for row in metrics["action_trace"] if row["citizen"] == agent)
            self.assertEqual(first["hidden_before"], model.initial_hidden().tolist())
        self.assertEqual(metrics["conservation_residual_A"], 0)
        self.assertEqual(metrics["conservation_residual_B"], 0)
        self.assertEqual(metrics["demand_residual"], 0)
        prepare_batch(sequences)
        values = [t["normalized_advantage"] for s in sequences for t in s]
        self.assertAlmostEqual(float(np.mean(values)), 0., places=12)
        self.assertAlmostEqual(float(np.std(values)), 1., places=5)

    def test_evaluation_does_not_call_critic_or_mutate_parameters(self):
        model = Network(24)
        before = model.digest(), model.updates
        with patch.object(self.world, "critic_state", side_effect=AssertionError("critic exposed")), \
             patch.object(model, "value", side_effect=AssertionError("critic used")):
            metrics, sequences = collect_episode(model, self.world, np.random.default_rng(8), training=False)
        self.assertEqual(before, (model.digest(), model.updates))
        self.assertTrue(all(t["critic_input"] is None for s in sequences for t in s))
        self.assertEqual(metrics["tick"], self.world.horizon)

    def test_checkpoint_roundtrip_binds_features_sources_weights_and_inference_only(self):
        model = Network(25, hidden=4, critic_hidden=5)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            model.save(path)
            restored = Network.load(path)
            self.assertEqual(model.digest(), restored.digest())
            self.assertEqual(model.actor_digest(), restored.actor_digest())
            self.assertEqual(model.critic_digest(), restored.critic_digest())
            self.assertFalse(restored.trainable)
            with self.assertRaises(ValueError):
                restored.update([])
            payload = json.loads(path.read_text())
            payload["parameters"]["actor_bo"][0] += .01
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "digest"):
                Network.load(path)
            model.save(path)
            payload = json.loads(path.read_text())
            payload["observation_contract"]["source_manifest"]["selective_communication_env.py"] = "changed"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "contract"):
                Network.load(path)

    def test_training_changes_both_networks_and_shares_world_manifests(self):
        results = [train(611, 4, recurrent=recurrent, batch_episodes=2, horizon=24)
                   for recurrent in (True, False)]
        for model, initial, statistics in results:
            self.assertEqual(model.updates, 2 * SETTINGS["ppo_epochs"])
            self.assertNotEqual(model.actor_digest(), initial.actor_digest())
            self.assertNotEqual(model.critic_digest(), initial.critic_digest())
            self.assertEqual(statistics["by_demand"]["recurring"]["episodes"], 2)
            self.assertEqual(statistics["by_demand"]["shutdown"]["episodes"], 2)
            self.assertEqual(statistics["agent_ticks"], 4 * 24 * 4)
            self.assertAlmostEqual(statistics["batch_records"][0]["entropy_coefficient"], .01)
            self.assertAlmostEqual(statistics["batch_records"][-1]["entropy_coefficient"], .0001)
        self.assertEqual(results[0][2]["training_world_seed_manifest_sha256"],
                         results[1][2]["training_world_seed_manifest_sha256"])

    def test_unread_training_is_equal_budget_and_has_matched_world_schedule(self):
        local = train(813, 2, communication="local", batch_episodes=1, horizon=16)
        unread = train(813, 2, communication="unread", batch_episodes=1, horizon=16)
        self.assertEqual(local[1].digest(), unread[1].digest())
        self.assertEqual(local[2]["training_world_seed_manifest_sha256"],
                         unread[2]["training_world_seed_manifest_sha256"])
        self.assertEqual(local[2]["world_ticks"], unread[2]["world_ticks"])
        self.assertEqual(unread[2]["training_communication"], "unread")


if __name__ == "__main__":
    unittest.main()
