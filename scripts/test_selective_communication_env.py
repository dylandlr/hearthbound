import copy
import random
import unittest

from distributed_demand_env import Evidence, Knowledge, Env as BaseEnv, mask as base_mask
from selective_communication_env import ACTIONS, CRITIC_FEATURES, FEATURES, F, Env, mask


def fixture(*, communication="local", dispatch_mode="selected", encounter=0):
    """Prescribed zero-tick memories for unit contracts, not emergence evidence."""
    world = Env(60217, agents=3, horizon=80, communication=communication,
                dispatch_mode=dispatch_mode, trace=True, run_id="selective-fixture")
    for actor in world._agents:
        actor.node = encounter
        actor.direct.clear()
        actor.reports.clear()
    world._refresh_local()
    for node in range(3):
        if node != encounter:
            witness = Evidence(f"{world._scope}:fixture:{node}", node, world._payload(node), 0, 0)
            world._agents[0].direct[node] = Knowledge(witness, "DIRECT", route=(0,))
    return world


def wait(world):
    return world.step({i: 0 for i in world.ready()})


class SelectiveEnvironmentTests(unittest.TestCase):
    def test_dimensions_and_own_decision_history(self):
        world = Env(51, agents=4, horizon=80)
        self.assertEqual((len(FEATURES), len(CRITIC_FEATURES), len(ACTIONS)), (52, 87, 11))
        actor = next(i for i, a in enumerate(world._agents) if a.node == 0)
        before = world.actor_obs(actor)
        self.assertEqual(sum(before[F[f"previous_action_{a}"]] for a in range(11)), 0)
        actions = {i: 0 for i in world.ready()}
        actions[actor] = 3
        world.step(actions)
        self.assertEqual(world.actor_obs(actor)[F["previous_action_3"]], 1)
        self.assertEqual(world.actor_obs(actor)[F["previous_decision_elapsed"]], 1 / 7)
        while actor not in world.ready():
            wait(world)
        self.assertEqual(world.actor_obs(actor)[F["previous_decision_elapsed"]], 4 / 7)
        self.assertEqual(len(world.critic_state(actor)), 87)
        self.assertTrue(all(0 <= x <= 1 for x in world.critic_state(actor)))

    def test_each_explicit_topic_and_physical_cost(self):
        for topic in range(3):
            world = fixture(encounter=(topic + 1) % 3)
            self.assertTrue(mask(world.actor_obs(0))[8 + topic])
            result = world.step({0: 8 + topic, 1: 0, 2: 0})
            sends = [e for e in world.events if e["event"] == "REPORT_SENT"]
            self.assertEqual(len(sends), 1)
            self.assertEqual(sends[0]["source_node"], topic)
            self.assertEqual(sends[0]["requested_topic"], topic)
            self.assertEqual(sends[0]["dispatch_mode"], "selected")
            self.assertEqual(result[0], 0)
            self.assertAlmostEqual(result[1][0], -.012)
            self.assertEqual(world.tick, 1)
            self.assertEqual(world.metrics()["chosen_topics"][topic], 1)
            self.assertEqual(world.metrics()["delivered"], 2)
            self.assertEqual(world.metrics()["conservation_residual"], 0)
            self.assertEqual(world.metrics()["demand_residual"], 0)

    def test_fixed_scheduler_intervention_preserves_inputs_and_opportunity(self):
        selected = fixture()
        fixed = fixture(dispatch_mode="fixed")
        for i in selected.ready():
            self.assertEqual(selected.actor_obs(i), fixed.actor_obs(i))
            self.assertEqual(mask(selected.actor_obs(i)), mask(fixed.actor_obs(i)))
        action = {0: 10, 1: 0, 2: 0}
        self.assertEqual(selected.step(action), fixed.step(action))
        self.assertEqual(selected.metrics()["chosen_topics"], [0, 0, 1])
        self.assertEqual(fixed.metrics()["chosen_topics"], [0, 1, 0])
        self.assertEqual(fixed.metrics()["requested_topics"], [0, 0, 1])
        self.assertEqual(selected.metrics()["attempts"], fixed.metrics()["attempts"])

    def test_private_remote_and_peer_states_do_not_enter_actor_or_mask(self):
        world = fixture()
        before, before_critic = world.actor_obs(0), world.critic_state(0)
        world._stocks[2][0] += 1
        world._depot[0] -= 1
        world._agents[1].direct[2] = world._agents[0].direct[2]
        world._schedule[28] = [(1, 0, 4), (2, 1, 4)]
        self.assertEqual(before, world.actor_obs(0))
        self.assertEqual(mask(before), mask(world.actor_obs(0)))
        self.assertNotEqual(before_critic, world.critic_state(0))
        # Even a training critic sees neither future orders nor the regime tag.
        current = world.critic_state(0)
        world._schedule[28] = [(1, 1, 2), (2, 0, 2)]
        world.demand = "shutdown"
        self.assertEqual(current, world.critic_state(0))

    def test_unread_transport_seals_content_but_not_packets(self):
        readable, unread = fixture(), fixture(communication="unread")
        action = {0: 10, 1: 0, 2: 0}
        self.assertEqual(readable.step(action), unread.step(action))
        self.assertEqual(readable.metrics()["delivered"], unread.metrics()["delivered"])
        self.assertEqual(readable.actor_obs(1)[F["workshop_2_known"]], 1)
        self.assertEqual(unread.actor_obs(1)[F["workshop_2_known"]], 0)
        self.assertEqual(unread.actor_obs(1)[F["topic_available_2"]], 1)
        self.assertIsNotNone(unread._knowledge(1, 2, sealed=True))
        wait(readable)
        wait(unread)
        self.assertGreater(readable.metrics()["read_report_inputs"], 0)
        self.assertEqual(unread.metrics()["read_report_inputs"], 0)

    def test_future_suppression_preserves_old_memory_and_sealed_forwarding(self):
        original = fixture()
        original.step({0: 10, 1: 0, 2: 0})
        readable, suppressed = original.fork("open"), original.fork("sealed")
        suppressed.set_report_read_suppression([1], future_only=True)
        self.assertEqual(readable.actor_obs(1), suppressed.actor_obs(1))
        for world in (readable, suppressed):
            world._depot[0] -= 1
            world._stocks[2][0] += 1
            fresh = Evidence(f"{world._scope}:new-fixture", 2, world._payload(2), world.tick, 0)
            world._agents[0].direct[2] = Knowledge(fresh, "DIRECT", route=(0,))
            world.step({0: 10, 1: 0, 2: 0})
        self.assertEqual(readable.metrics()["delivered"], suppressed.metrics()["delivered"])
        self.assertEqual(readable.actor_obs(1)[F["workshop_2_stock_a"]], 1 / 8)
        self.assertEqual(suppressed.actor_obs(1)[F["workshop_2_stock_a"]], 0)
        self.assertEqual(suppressed._knowledge(1, 2).evidence.observed_tick, 0)
        self.assertEqual(suppressed._knowledge(1, 2, sealed=True).evidence.observed_tick, 1)
        # Other recipients remain unaffected by the recipient-specific intervention.
        self.assertEqual(readable.actor_obs(2), suppressed.actor_obs(2))
        while suppressed.tick <= 24:
            wait(suppressed)
        self.assertIsNone(suppressed._knowledge(1, 2))
        self.assertIsNotNone(suppressed._knowledge(1, 2, sealed=True))

    def test_suppression_installed_before_receipt_hides_only_target_reader(self):
        readable, suppressed = fixture(), fixture()
        suppressed.set_report_read_suppression([1], future_only=True)
        for i in readable.ready():
            self.assertEqual(readable.actor_obs(i), suppressed.actor_obs(i))
        actions = {0: 10, 1: 0, 2: 0}
        self.assertEqual(readable.step(actions), suppressed.step(actions))
        self.assertEqual(readable.metrics()["delivered"], suppressed.metrics()["delivered"])
        self.assertEqual(suppressed.actor_obs(1)[F["workshop_2_known"]], 0)
        self.assertEqual(suppressed.actor_obs(2)[F["workshop_2_known"]], 1)
        self.assertEqual(readable.actor_obs(2), suppressed.actor_obs(2))
        self.assertEqual(suppressed.actor_obs(1)[F["topic_available_2"]], 1)

    def test_all_report_suppression_keeps_direct_observations_readable(self):
        world = fixture()
        world.step({0: 10, 1: 0, 2: 0})
        world.set_report_read_suppression([1], future_only=False)
        self.assertEqual(world.actor_obs(1)[F["workshop_2_known"]], 0)
        self.assertEqual(world.actor_obs(1)[F["depot_known"]], 1)
        world.step({0: 0, 1: 3, 2: 0})
        while 1 not in world.ready():
            wait(world)
        self.assertEqual(world.actor_obs(1)[F["workshop_2_known"]], 1)
        self.assertEqual(world._knowledge(1, 2).origin, "DIRECT")

    def test_fork_has_shared_prefix_and_new_future_scope(self):
        original = fixture()
        original.step({0: 10, 1: 0, 2: 0})
        prefix = copy.deepcopy(original.events)
        fork = original.fork("fork-test")
        self.assertEqual(fork.events[:len(prefix)], prefix)
        self.assertEqual(fork._agents[1].reports[2], original._agents[1].reports[2])
        for i in original.ready():
            self.assertEqual(original.actor_obs(i), fork.actor_obs(i))
        old_order_id = fork._orders[0].order_id
        wait(fork)
        self.assertEqual(fork._orders[0].order_id, old_order_id)
        direct = [e for e in fork.events[len(prefix):] if e["event"] == "DIRECT_OBSERVATION"]
        self.assertTrue(all(e["run_id"] == "fork-test" for e in direct))
        self.assertTrue(all(":run:fork-test:" in e["observation_id"] for e in direct))
        self.assertEqual(original.tick, 1)
        self.assertEqual(fork.tick, 2)

    def test_bad_joint_action_is_atomic_and_cannot_forward_same_tick(self):
        world = fixture()
        before = copy.deepcopy(world.__dict__)
        with self.assertRaises(ValueError):
            world.step({0: 10, 1: 10, 2: 0})
        self.assertEqual(world.__dict__, before)
        # Citizen 1 has no remote packet before citizen 0's simultaneous send.
        self.assertFalse(mask(world.actor_obs(1))[10])
        world.step({0: 10, 1: 0, 2: 0})
        sent = [e for e in world.events if e["event"] == "REPORT_SENT"]
        self.assertEqual([e["sender"] for e in sent], [0])
        self.assertTrue(mask(world.actor_obs(1))[10])

    def test_original_witness_timestamp_and_parent_survive_forwarding(self):
        world = fixture()
        world._agents[2].node = 1
        world._agents[2].direct.clear()
        world._refresh_local()
        world.step({0: 10, 1: 0, 2: 0})
        first = next(e for e in world.events if e["event"] == "REPORT_DELIVERED")
        world.step({0: 0, 1: 2, 2: 0})
        while 1 not in world.ready():
            wait(world)
        world.step({i: 10 if i == 1 else 0 for i in world.ready()})
        forwarded = [e for e in world.events if e["event"] == "REPORT_DELIVERED" and e["sender"] == 1]
        self.assertEqual(len(forwarded), 1)
        event = forwarded[0]
        self.assertEqual(event["observation_id"], first["observation_id"])
        self.assertEqual(event["observed_tick"], first["observed_tick"])
        self.assertEqual(event["original_observer"], 0)
        self.assertEqual(event["parent_message_id"], first["message_id"])
        self.assertEqual(event["route"], (0, 1, 2))

    def test_no_relay_and_instant_do_not_create_direct_witnesses(self):
        for protocol in ("no_relay", "instant"):
            world = fixture(communication=protocol)
            world.step({0: 10, 1: 0, 2: 0})
            self.assertFalse(mask(world.actor_obs(1))[10])
            self.assertNotIn(2, world._agents[1].direct)

    def test_mapped_actions_preserve_frozen_physics_and_all_base_ledgers(self):
        for dispatch in ("selected", "fixed"):
            base = BaseEnv(60231, agents=4, horizon=80, run_id="equivalence")
            world = Env(60231, agents=4, horizon=80, run_id="equivalence", dispatch_mode=dispatch)
            rng = random.Random(8831)
            while not base.done:
                old, new = {}, {}
                for i in base.ready():
                    self.assertEqual(base.obs(i), world.actor_obs(i)[:37])
                    choices = [a for a, allowed in enumerate(base_mask(base.obs(i))) if allowed]
                    old[i] = rng.choice(choices)
                    if old[i] == 8:
                        topic = base._share(i)[0].evidence.node
                        new[i] = 8 + topic if dispatch == "selected" else next(
                            a for a in range(10, 7, -1) if mask(world.actor_obs(i))[a])
                    else:
                        new[i] = old[i]
                self.assertEqual(base.step(old), world.step(new))
                metrics = world.metrics()
                for key, value in base.metrics().items():
                    self.assertEqual(value, metrics[key], key)
                self.assertEqual(sum(metrics["chosen_topics"]), metrics["attempts"])
                self.assertEqual(metrics["conservation_residual"], 0)
                self.assertEqual(metrics["demand_residual"], 0)

    def test_invalid_observation_and_intervention_inputs(self):
        world = fixture()
        with self.assertRaises(ValueError):
            mask(world.actor_obs(0)[:-1])
        with self.assertRaises(ValueError):
            mask((float("nan"),) + world.actor_obs(0)[1:])
        for recipients in ([3], [True], ["1"], None):
            before = copy.deepcopy(world.__dict__)
            with self.assertRaises(ValueError):
                world.set_report_read_suppression(recipients)
            self.assertEqual(world.__dict__, before)
        with self.assertRaises(ValueError):
            world.fork(world.run_id)
        with self.assertRaises(ValueError):
            Env(1, dispatch_mode="unrecognized")


if __name__ == "__main__":
    unittest.main()
