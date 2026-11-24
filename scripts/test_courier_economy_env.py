"""Mechanism tests only: passing these is not evidence of learned occupation."""
import copy
import random
import unittest
from courier_economy_env import ACTIONS, COORDINATES, Env, Evidence, F, Knowledge, TTL, mask, scripted_local


class CourierEconomyTests(unittest.TestCase):
    def move_to(self, env, agent, node):
        """Execute real travel while the other citizens wait."""
        self.assertIn(agent, env.ready())
        choices = {i: 0 for i in env.ready()}
        choices[agent] = node + 1
        env.step(choices)
        while agent not in env.ready() and not env.done:
            env.step({i: 0 for i in env.ready()})

    def share(self, env, sender):
        choices = {i: 0 for i in env.ready()}
        choices[sender] = 8
        return env.step(choices)

    def scenario(self, communication="local", agents=3):
        env = Env(51, agents=agents, horizon=96, communication=communication, trace=True)
        self.move_to(env, 0, 2)
        self.move_to(env, 0, 0)
        # Engineered scheduler would choose unshared hub first. Mark only the
        # current hub sight as already sent to isolate the source-report test.
        actor = env._agents[0]
        actor.shared[0] = actor.direct[0].evidence.observation_id
        self.share(env, 0)
        return env

    def test_run_scope_changes_provenance_without_changing_physics_or_policy(self):
        a = Env(51, agents=2, trace=True, run_id="eval:17:51:trained:local")
        b = Env(51, agents=2, trace=True, run_id="eval:23:51:trained:local")
        self.assertEqual(a._stock, b._stock)
        self.assertEqual(a._priorities, b._priorities)
        self.assertEqual([a.obs(i) for i in a.ready()], [b.obs(i) for i in b.ready()])
        for env in (a, b):
            self.move_to(env, 0, 2)
            self.move_to(env, 0, 0)
            env._agents[0].shared[0] = env._agents[0].direct[0].evidence.observation_id
            self.share(env, 0)
        self.assertEqual(a.metrics(), b.metrics())
        a_ids = {event[field] for event in a.events for field in ("observation_id", "message_id") if field in event}
        b_ids = {event[field] for event in b.events for field in ("observation_id", "message_id") if field in event}
        self.assertFalse(a_ids & b_ids)
        self.assertTrue(all(event["run_id"] == a.run_id for event in a.events))
        sent = next(e for e in a.events if e["event"] == "REPORT_SENT")
        delivered = next(e for e in a.events if e["event"] == "REPORT_DELIVERED")
        self.assertEqual(sent["quantities"], delivered["quantities"])
        self.assertIsNone(sent["parent_message_id"])
        self.assertIsNone(delivered["parent_message_id"])
        with self.assertRaises(ValueError):
            Env(51, run_id="")
        with self.assertRaises(ValueError):
            Env(51, run_id="bad scope with spaces")

    def test_remote_stocks_and_masks_are_private(self):
        env = Env(2)
        before = [env.obs(i) for i in range(env.agents)]
        env._stock = [6 - n for n in env._stock]
        after = [env.obs(i) for i in range(env.agents)]
        self.assertEqual(before, after)
        self.assertEqual([mask(o) for o in before], [mask(o) for o in after])
        self.assertTrue(all(o[F["site_1_known"]] == 0 for o in before))

    def test_nonlocal_peer_state_does_not_leak(self):
        env = Env(2, agents=2)
        self.move_to(env, 1, 1)
        before = env.obs(0)
        env._agents[1].cargo = 0
        env._agents[1].direct.clear()
        self.assertEqual(before, env.obs(0))

    def test_travel_takes_elapsed_ticks_and_no_remote_share(self):
        env = Env(2, agents=2, trace=True)
        before = env.tick
        self.move_to(env, 0, 1)
        self.assertEqual(env.tick - before, abs(COORDINATES[1]))
        self.assertEqual(env._agents[0].node, 1)
        self.assertFalse(mask(env.obs(0))[8])
        self.assertNotIn(1, env._agents[1].reports)
        self.assertEqual(env.metrics()["travel_ticks"], abs(COORDINATES[1]))

    def test_physical_delivery_preserves_witness_and_age(self):
        env = self.scenario()
        entry = env._agents[1].reports[2]
        self.assertEqual(entry.origin, "REPORT")
        self.assertEqual(entry.evidence.observer, 0)
        self.assertEqual(entry.sender, 0)
        self.assertEqual(entry.route, (0, 1))
        self.assertLess(entry.evidence.observed_tick, env.tick)
        self.assertEqual(env._agents[0].direct[2].evidence, entry.evidence)
        self.assertEqual(env.metrics()["cross_site_deliveries"], 2)
        self.assertEqual(env.metrics()["produced"], 0)

    def test_two_hop_forwarding_retains_original_identity(self):
        env = self.scenario()
        # Third citizen was present for first handoff; remove that report only
        # to exercise a fresh second-hop recipient while keeping real positions.
        env._agents[2].reports.clear()
        sender = env._agents[1]
        sender.shared[0] = sender.direct[0].evidence.observation_id
        before = sender.reports[2]
        self.share(env, 1)
        forwarded = env._agents[2].reports[2]
        self.assertEqual(before.evidence, forwarded.evidence)
        self.assertEqual(forwarded.sender, 1)
        self.assertEqual(forwarded.route, (0, 1, 2))
        self.assertEqual(forwarded.origin, "REPORT")
        event = next(e for e in reversed(env.events) if e["event"] == "REPORT_DELIVERED")
        self.assertEqual(event["parent_message_id"], before.message_id)
        self.assertEqual(event["quantities"], before.evidence.quantities)
        self.assertEqual(env.metrics()["forwarded"], 1)
        self.assertGreater(env.metrics()["loop_rejected"], 0)

    def test_expiry_uses_original_observation_time(self):
        env = self.scenario()
        original = env._agents[1].reports[2].evidence.observed_tick
        while env.tick <= original + TTL:
            env.step({i: 0 for i in env.ready()})
        self.assertNotIn(2, env._agents[1].reports)
        self.assertEqual(env.obs(1)[F["site_2_known"]], 0)
        self.assertGreater(env.metrics()["expired"], 0)

    def test_duplicate_does_not_refresh_or_reward(self):
        env = self.scenario()
        payload = env._agents[0].direct[2]
        before = env._agents[1].reports[2]
        self.assertFalse(env._admit(1, 0, payload, "duplicate"))
        self.assertEqual(env._agents[1].reports[2], before)
        self.assertEqual(env.metrics()["duplicates"], 1)
        self.assertEqual(env.metrics()["produced"], 0)

    def test_delivery_and_policy_input_are_distinct(self):
        env = self.scenario()
        self.assertGreater(env.metrics()["delivered"], 0)
        self.assertEqual(env.metrics()["read_report_inputs"], 0)
        env.step({i: 0 for i in env.ready()})
        self.assertGreater(env.metrics()["read_report_inputs"], 0)
        self.assertEqual(env.metrics()["report_present_for_travel"], 0)

    def test_blocked_and_unread_controls(self):
        blocked = self.scenario("no_messages")
        unread = self.scenario("unread")
        self.assertEqual(blocked.metrics()["delivered"], 0)
        self.assertEqual(blocked.metrics()["blocked"], 2)
        self.assertGreater(unread.metrics()["delivered"], 0)
        self.assertEqual(unread.obs(1)[F["site_2_known"]], 0)
        unread.step({i: 0 for i in unread.ready()})
        self.assertEqual(unread.metrics()["read_report_inputs"], 0)
        # Transmitting costs have the same sign/amount without production reward.
        self.assertAlmostEqual(blocked.metrics()["per_agent"][0]["personal_reward"],
                               self.scenario("local").metrics()["per_agent"][0]["personal_reward"])

    def test_unread_can_transport_sealed_reports_without_reading_content(self):
        env = self.scenario("unread")
        env._agents[2].reports.clear()
        sender = env._agents[1]
        sender.shared[0] = sender.direct[0].evidence.observation_id
        self.assertEqual(env.obs(1)[F["site_2_known"]], 0)
        self.assertTrue(mask(env.obs(1))[8])
        self.share(env, 1)
        self.assertEqual(env._agents[2].reports[2].route, (0, 1, 2))
        self.assertEqual(env.metrics()["forwarded"], 1)
        self.assertEqual(env.metrics()["read_report_inputs"], 0)

    def test_no_relay_can_receive_but_cannot_forward(self):
        env = self.scenario("no_relay")
        self.assertEqual(env.obs(1)[F["site_2_report"]], 1)
        actor = env._agents[1]
        actor.shared[0] = actor.direct[0].evidence.observation_id
        self.assertIsNone(env._share_payload(1))
        self.assertFalse(mask(env.obs(1))[8])

    def test_same_tick_new_receipt_cannot_be_forwarded(self):
        env = Env(51, agents=3, trace=True)
        self.move_to(env, 0, 2)
        self.move_to(env, 0, 0)
        env._agents[0].shared[0] = env._agents[0].direct[0].evidence.observation_id
        env.step({0: 8, 1: 8, 2: 0})
        sent = [e for e in env.events if e["event"] == "REPORT_SENT" and e["sender"] == 1]
        self.assertEqual(len(sent), 1)
        self.assertIn(":1:0:", sent[0]["observation_id"])
        self.assertEqual(env.metrics()["forwarded"], 0)

    def test_direct_reobservation_wins_equal_tick(self):
        env = self.scenario()
        actor = env._agents[1]
        report = actor.reports[2]
        direct_evidence = Evidence("own-equal", 2, (0,), report.evidence.observed_tick, 1)
        actor.direct[2] = Knowledge(direct_evidence, "DIRECT", route=(1,))
        self.assertEqual(env._knowledge(1, 2).origin, "DIRECT")
        self.assertEqual(env.obs(1)[F["site_2_quantity"]], 0)

    def test_invalid_actions_rejected_before_any_mutation(self):
        env = Env(2)
        before = copy.deepcopy(env.__dict__)
        with self.assertRaises(ValueError):
            env.step({0: 2, 1: 7, 2: 0, 3: 0})
        self.assertEqual(env.__dict__, before)
        with self.assertRaises(ValueError):
            env.step({0: 2})
        self.assertEqual(env.__dict__, before)

    def test_matching_treatments_have_identical_initial_physics(self):
        worlds = [Env(31, communication=p) for p in ("local", "no_messages", "unread", "no_relay", "instant")]
        for other in worlds[1:]:
            self.assertEqual(worlds[0]._stock, other._stock)
            self.assertEqual(worlds[0]._kinds, other._kinds)
            self.assertEqual(worlds[0]._priorities, other._priorities)
            self.assertEqual([a.travel_cost for a in worlds[0]._agents],
                             [a.travel_cost for a in other._agents])
        instant = worlds[-1]
        self.assertEqual(instant.obs(0)[F["site_1_known"]], 1)
        self.assertEqual(instant._knowledge(0, 1).origin, "PUBLIC")
        self.assertNotIn(1, instant._agents[0].direct)

    def test_conservation_and_colony_reward_match_products(self):
        for protocol in ("local", "no_messages", "unread", "instant", "no_relay"):
            for seed in range(4):
                env = Env(seed, agents=4, horizon=64, communication=protocol)
                rng = random.Random(seed)
                reward = 0.
                while not env.done:
                    actions = {i: rng.choice([a for a, valid in enumerate(mask(env.obs(i))) if valid])
                               for i in env.ready()}
                    colony, personal, done = env.step(actions)
                    reward += colony
                    result = env.metrics()
                    self.assertEqual(result["conservation_residual_A"], 0)
                    self.assertEqual(result["conservation_residual_B"], 0)
                    self.assertTrue(all(r <= 0 for r in personal))
                self.assertEqual(reward, env.metrics()["produced"])

    def test_productive_local_baseline_reaches_real_synthetic_output(self):
        env = Env(51, agents=4, horizon=96)
        while not env.done:
            env.step({i: scripted_local(env.obs(i)) for i in env.ready()})
        result = env.metrics()
        self.assertGreater(result["produced"], 0)
        self.assertLessEqual(result["produced"], result["attainable_material_bound"])
        self.assertEqual(result["conservation_residual"], 0)
        self.assertEqual(result["attempts"], 0)
        self.assertEqual(result["minecraft_worlds"], 0)

    def test_allows_100_agents_without_role_or_identity_features(self):
        env = Env(7, agents=100, horizon=1)
        env.step({i: 0 for i in env.ready()})
        self.assertTrue(env.done)
        self.assertEqual(len(env.metrics()["per_agent"]), 100)
        self.assertNotIn("role", F)
        self.assertNotIn("agent_id", F)


if __name__ == "__main__":
    unittest.main()
