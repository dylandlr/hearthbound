"""Inference alias checks; no training or held-out performance evaluation."""
import copy
from pathlib import Path
import tempfile
import unittest

from colony_task_env import Env, mask
from colony_allocation_alias import choose, decision_mask, is_current_inspection
from train_colony_task_allocation import Network, observation_contract


class AliasTests(unittest.TestCase):
    def place_by_inspection(self, env, destinations):
        env.step({agent: site + 1 for agent, site in destinations.items()})
        while len(env.ready()) != env.agents:
            env.step({agent: 0 for agent in env.ready()})

    def compare_aliases(self, env, other_actions):
        site = next(i for i, source in enumerate(env._sites)
                    if source.position == env._agents[0].position)
        original, waiting = copy.deepcopy(env), copy.deepcopy(env)
        inspect_action = site + 1
        self.assertTrue(is_current_inspection(original.obs(0), inspect_action))
        a = original.step({0: inspect_action, **other_actions})
        b = waiting.step({0: 0, **other_actions})
        self.assertEqual(a, b)
        self.assertEqual(original.tick, waiting.tick)
        self.assertEqual(original.done, waiting.done)
        self.assertEqual(original.ready(), waiting.ready())
        self.assertEqual(original._sites, waiting._sites)
        self.assertEqual(original._agents, waiting._agents)
        for agent in range(env.agents):
            self.assertEqual(original.obs(agent), waiting.obs(agent))
        metrics_a, metrics_b = original.metrics(), waiting.metrics()
        self.assertEqual(metrics_a.pop("totalinspections"), metrics_b.pop("totalinspections") + 1)
        self.assertEqual(metrics_a, metrics_b)
        physical_a = [e for e in original.events if e["event"] != "INSPECT_STARTED"]
        physical_b = [e for e in waiting.events if e["event"] != "INSPECT_STARTED"]
        self.assertEqual(physical_a, physical_b)

    def test_alias_equivalence_positive_and_empty_with_other_waiting(self):
        for seed in (101, 103, 107, 109):
            for empty in (False, True):
                with self.subTest(seed=seed, empty=empty):
                    env = Env(seed)
                    if empty:
                        env._sites[0].stock = 0
                        env._initial = [sum(s.stock for s in env._sites if s.kind == k)
                                        for k in (0, 1)]
                    # Actor 1 stays at hub, while actor 0 travels and inspects.
                    env.step({0: 1, 1: 0})
                    while 0 not in env.ready():
                        env.step({agent: 0 for agent in env.ready()})
                    self.compare_aliases(env, {1: 0})

    def test_alias_equivalence_while_another_actor_hauls(self):
        for seed in (101, 103, 107, 109):
            for empty in (False, True):
                with self.subTest(seed=seed, empty=empty):
                    env = Env(seed)
                    if empty:
                        env._sites[0].stock = 0
                        env._initial = [sum(s.stock for s in env._sites if s.kind == k)
                                        for k in (0, 1)]
                    self.place_by_inspection(env, {0: 0, 1: 1})
                    self.assertTrue(mask(env.obs(1))[6])
                    self.compare_aliases(env, {1: 6})

    def test_alias_equivalence_with_an_already_busy_peer(self):
        for seed in (101, 103, 107, 109):
            with self.subTest(seed=seed):
                env = Env(seed)
                env.step({0: 1, 1: 0})
                while 0 not in env.ready():
                    env.step({agent: 0 for agent in env.ready()})
                far = next(i for i, s in enumerate(env._sites) if abs(s.position) >= 2)
                env.step({0: 0, 1: 1 + far})
                self.assertEqual(env.ready(), [0])
                self.compare_aliases(env, {})

    def test_only_current_fresh_inspection_is_removed(self):
        env = Env(101)
        self.place_by_inspection(env, {0: 0, 1: 1})
        observation = env.obs(0)
        self.assertTrue(is_current_inspection(observation, 1))
        full, pruned = decision_mask(observation), decision_mask(observation, prune=True)
        self.assertEqual(full, mask(observation))
        self.assertEqual([i for i, (a, b) in enumerate(zip(full, pruned)) if a != b], [1])
        self.assertTrue(pruned[0])
        self.assertEqual(pruned[5:], full[5:])
        for action in (0, 2, 5, -1, 9, True):
            self.assertFalse(is_current_inspection(observation, action))

    def test_unknown_and_stale_observations_do_not_hard_prune(self):
        env = Env(101)
        self.place_by_inspection(env, {0: 0, 1: 1})
        for index, value in ((9, 0.), (11, .1)):
            observation = list(env.obs(0))
            observation[index] = value
            self.assertFalse(is_current_inspection(tuple(observation), 1))
            self.assertTrue(decision_mask(tuple(observation), prune=True)[1])

    def test_hidden_stock_cannot_change_pruning(self):
        env = Env(101)
        self.place_by_inspection(env, {0: 0, 1: 1})
        altered = copy.deepcopy(env)
        for site in altered._sites:
            site.stock = 0
        for agent in range(2):
            self.assertEqual(env.obs(agent), altered.obs(agent))
            self.assertEqual(decision_mask(env.obs(agent), prune=True),
                             decision_mask(altered.obs(agent), prune=True))

    def test_wait_remains_even_when_no_haul_is_known(self):
        env = Env(101)
        self.assertTrue(decision_mask(env.obs(0), prune=True)[0])
        self.assertFalse(any(decision_mask(env.obs(0), prune=True)[5:]))
        env._sites[0].stock = 0
        self.place_by_inspection(env, {0: 0, 1: 1})
        pruned = decision_mask(env.obs(0), prune=True)
        self.assertFalse(pruned[1])
        self.assertFalse(pruned[5])
        self.assertTrue(pruned[0])

    def test_chooser_reranks_heads_instead_of_forcing_wait_or_haul(self):
        env = Env(101)
        self.place_by_inspection(env, {0: 0, 1: 1})
        class Scores:
            def values(self, observation):
                return (1., 10., 9., 0., 0., 8., 0., 0., 0.)
        self.assertEqual(choose(Scores(), env.obs(0)), 1)
        self.assertEqual(choose(Scores(), env.obs(0), prune=True), 2)
        class WaitWins:
            def values(self, observation):
                return (9., 10., 1., 0., 0., 8., 0., 0., 0.)
        self.assertEqual(choose(WaitWins(), env.obs(0), prune=True), 0)

    def test_checkpoint_contract_is_unchanged_by_inference_intervention(self):
        model = Network(7)
        contract = observation_contract()
        digest = model.digest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            model.save(path)
            loaded = Network.load(path)
            env = Env(101)
            self.place_by_inspection(env, {0: 0, 1: 1})
            self.assertEqual(choose(loaded, env.obs(0)), loaded.greedy(env.obs(0)))
            choose(loaded, env.obs(0), prune=True)
            self.assertEqual(loaded.digest(), digest)
            self.assertEqual(observation_contract(), contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
