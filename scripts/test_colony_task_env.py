"""Adversarial synthetic-environment checks, not Minecraft acceptance."""
import copy
import random
import unittest

from colony_task_env import ACTIONS, FEATURES, HUB_SCALE, Env, mask, scripted_balance, scripted_nearest


class ColonyTaskTests(unittest.TestCase):
    def finish_tasks(self, env):
        while not env.done and not env.ready():
            env.step({})

    def set_sites(self, env, positions=(1, 2, 3, 4), quantities=(1, 1, 1, 1)):
        for i, source in enumerate(env._sites):
            source.position, source.kind, source.stock = positions[i], i % 2, quantities[i]
        env._initial = [sum(s.stock for s in env._sites if s.kind == k) for k in (0, 1)]

    def test_initial_dimensions_and_unknown_stock(self):
        env = Env(4)
        self.assertEqual(len(FEATURES), 38)
        self.assertEqual(len(ACTIONS), 9)
        for i in env.ready():
            obs = env.obs(i)
            self.assertEqual(len(obs), 38)
            self.assertEqual(obs[5], 1)
            self.assertTrue(all(obs[9 + 8 * j] == 0 for j in range(4)))
            self.assertEqual(mask(obs), (True,) * 5 + (False,) * 4)

    def test_hidden_stock_changes_do_not_change_obs_or_mask(self):
        env = Env(7)
        hidden = copy.deepcopy(env)
        for source in hidden._sites:
            source.stock = 0
        for i in env.ready():
            self.assertEqual(env.obs(i), hidden.obs(i))
            self.assertEqual(mask(env.obs(i)), mask(hidden.obs(i)))

    def test_obs_has_no_global_rng_side_effect(self):
        random.seed(81)
        state = random.getstate()
        env = Env(13)
        env.obs(0)
        self.assertEqual(random.getstate(), state)

    def test_seed_and_action_independent_priorities(self):
        first, second = Env(11), Env(11)
        self.assertEqual(first.obs(0), second.obs(0))
        self.assertEqual(first._priorities, second._priorities)
        first.step({0: 1, 1: 0})
        second.step({0: 2, 1: 0})
        self.assertEqual(first._priorities, second._priorities)
        self.assertEqual([(s.position, s.kind, s.stock) for s in first._sites],
                         [(s.position, s.kind, s.stock) for s in second._sites])

    def test_maps_and_resource_slots_are_permuted_across_seeds(self):
        maps = {tuple((s.position, s.kind) for s in Env(seed)._sites) for seed in range(12)}
        self.assertGreater(len(maps), 1)
        self.assertGreater(len({tuple(s.kind for s in Env(seed)._sites) for seed in range(12)}), 1)

    def test_ood_normalization_and_scarcity(self):
        env = Env(7, regime="long_routes")
        self.assertTrue(all(7 <= abs(s.position) <= 12 for s in env._sites))
        self.assertTrue(all(0 <= v <= 1 for v in env.obs(0)))
        scarce = Env(7, regime="scarce_b")
        self.assertTrue(all(s.stock == 1 for s in scarce._sites if s.kind == 1))

    def test_invalid_simultaneous_input_has_no_effect(self):
        env = Env(2)
        before = copy.deepcopy(env.metrics()), env.obs(0), list(env.events)
        for actions in ({0: 0}, {0: 0, 1: 5}, {0: True, 1: 0}, {0: 0, 1: 0, 2: 0}):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                env.step(actions)
            self.assertEqual((env.metrics(), env.obs(0), env.events), before)

    def test_inspection_travel_and_direct_haul_sequence(self):
        env = Env(2, agents=1)
        self.set_sites(env, positions=(3, 4, 5, 6))
        env.step({0: 1})
        self.assertEqual(env.tick, 1)
        self.assertEqual(env.ready(), [])
        self.assertEqual(env.obs(0)[9], 0)
        env.step({})
        env.step({})
        self.assertEqual(env.tick, 3)
        self.assertEqual(env.ready(), [0])
        self.assertTrue(mask(env.obs(0))[5])
        env.step({0: 5})
        self.assertEqual(env.metrics()["transit_items"], 1)
        env.step({})
        env.step({})
        self.assertEqual(env.tick, 6)
        self.assertEqual(env.metrics()["deliveredA"], 1)
        self.assertEqual(env.obs(0)[5], 1)
        self.assertEqual(env.metrics()["conservation_residual"], 0)

    def test_haul_cannot_target_a_different_site(self):
        env = Env(2, agents=1)
        self.set_sites(env)
        env.step({0: 1})
        self.assertTrue(mask(env.obs(0))[5])
        self.assertFalse(mask(env.obs(0))[6])
        with self.assertRaises(ValueError):
            env.step({0: 6})

    def test_simultaneous_contention_not_hidden_mask(self):
        env = Env(8)
        self.set_sites(env)
        env.step({0: 1, 1: 1})
        self.assertTrue(mask(env.obs(0))[5])
        self.assertTrue(mask(env.obs(1))[5])
        colony, personal, done = env.step({0: 5, 1: 5})
        self.assertEqual(env.metrics()["deliveredA"], 1)
        self.assertEqual(env.metrics()["denials"], 1)
        self.assertAlmostEqual(min(personal), -.052)
        self.assertAlmostEqual(max(personal), -.002)
        self.assertEqual(colony, 0)
        self.assertFalse(done)
        self.assertEqual(env.metrics()["conservation_residual_A"], 0)

    def test_direct_sensing_refreshes_only_at_idle_current_site(self):
        env = Env(8)
        self.set_sites(env)
        env.step({0: 1, 1: 0})
        env._sites[0].stock = 0
        # An evaluator changing hidden world truth does not itself mutate a snapshot.
        self.assertTrue(mask(env.obs(0))[5])
        env.step({0: 0, 1: 0})
        self.assertEqual(env.obs(0)[10], 0)
        self.assertFalse(mask(env.obs(0))[5])
        self.assertEqual(env.obs(1)[9], 0)

    def test_public_intent_has_no_hidden_stock(self):
        env = Env(3)
        self.set_sites(env, positions=(3, 4, 5, 6))
        env.step({0: 1, 1: 0})
        view = env.obs(1)
        self.assertEqual(view[13], 1)
        self.assertEqual(view[9], 0)
        hidden = copy.deepcopy(env)
        hidden._sites[0].stock = 0
        self.assertEqual(view, hidden.obs(1))

    def test_fixed_horizon_no_early_success_and_no_delivery_after_horizon(self):
        env = Env(6, horizon=8)
        self.set_sites(env, positions=(1, -1, 3, 4))
        env.step({0: 1, 1: 2})
        reward, _, done = env.step({0: 5, 1: 6})
        self.assertEqual(reward, 1)
        self.assertFalse(done)
        self.assertEqual(env.metrics()["produced"], 1)
        while not env.done:
            env.step({i: 0 for i in env.ready()})
        self.assertEqual(env.tick, 8)
        self.assertEqual(env.ready(), [])
        with self.assertRaises(ValueError):
            env.step({})
        transit = Env(6, agents=1, horizon=4)
        self.set_sites(transit, positions=(3, 4, 5, 6))
        transit.step({0: 1})
        transit.step({})
        transit.step({})
        transit.step({0: 5})
        self.assertTrue(transit.done)
        self.assertEqual(transit.metrics()["transit_items"], 1)
        self.assertEqual(transit.metrics()["deliveredA"], 0)
        self.assertEqual(transit.metrics()["conservation_residual"], 0)
        self.assertEqual(transit.metrics()["totaltravel"], 4)

    def test_priority_is_independent_of_action_dictionary_order(self):
        left, right = Env(8), Env(8)
        for env in (left, right):
            self.set_sites(env)
            env.step({0: 1, 1: 1})
        result_left = left.step({0: 5, 1: 5})
        result_right = right.step({1: 5, 0: 5})
        self.assertEqual(result_left, result_right)
        self.assertEqual(left.metrics(), right.metrics())
        self.assertEqual(left.events, right.events)

    def test_balance_compares_hub_and_transit_in_matching_units(self):
        obs = list(Env(5).obs(0))
        obs[1:5] = [1 / HUB_SCALE, 0., 0., .5]  # Hub A=1 and in-transit B=1, two actors.
        for site in range(4):
            offset = 6 + 8 * site
            obs[offset:offset + 8] = [float(site % 2 == 0), float(site % 2 == 1),
                                     .8 if site == 0 else .1, 1.,
                                     1. if site < 2 else 0., 0., 0., 0.]
        # Equal raw supply: take the nearby B opportunity, not an imaginary A deficit.
        self.assertEqual(scripted_balance(tuple(obs), agents=2), 2)
        for agents in (0, -1, True):
            with self.subTest(agents=agents), self.assertRaises(ValueError):
                scripted_balance(tuple(obs), agents=agents)

    def test_hub_scaling_preserves_full_finite_inventory(self):
        env = Env(5)
        env._hub = [8, 4]
        observation = env.obs(0)
        self.assertEqual(observation[1], 1.)
        self.assertEqual(observation[2], .5)
        self.assertEqual(observation[1] * HUB_SCALE, 8)
        self.assertTrue(all(0 <= value <= 1 for value in observation))
        mask(observation)

    def test_every_busy_tick_has_effort_cost(self):
        env = Env(9, horizon=7)
        self.set_sites(env, positions=(6, 5, 4, 3))
        totals = [0., 0.]
        for tick in range(7):
            actions = {i: (1 if tick == 0 else 0) for i in env.ready()}
            _, personal, _ = env.step(actions)
            totals = [a + b for a, b in zip(totals, personal)]
        for reward in totals:
            self.assertAlmostEqual(reward, -.014)

    def test_all_policies_conserve_resources_every_tick(self):
        for agents in (2, 4):
            for seed in range(8):
                for policy in (scripted_nearest, scripted_balance):
                    env = Env(seed, agents=agents, horizon=64)
                    while not env.done:
                        env.step({i: (policy(env.obs(i), agents=agents) if policy is scripted_balance
                                      else policy(env.obs(i))) for i in env.ready()})
                        metrics = env.metrics()
                        self.assertEqual(metrics["conservation_residual_A"], 0)
                        self.assertEqual(metrics["conservation_residual_B"], 0)
                        self.assertLessEqual(metrics["produced"], metrics["attainable_material_bound"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
