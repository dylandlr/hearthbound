"""Mechanism contracts; synthetic checks do not establish an emergent occupation."""
import copy
import random
import unittest

from distributed_demand_env import (ACTIONS, CAPACITY, COORDINATES, DEMAND_REGIMES,
    Env, Evidence, F, Knowledge, ORDER_LIFETIME, PERIOD, PROTOCOLS, TTL, mask, scripted_local)


class DemandEnvironmentTests(unittest.TestCase):
    def setup_nodes(self, env, nodes):
        self.assertEqual(env.tick, 0)
        for actor, node in zip(env._agents, nodes):
            actor.node = node
            actor.direct.clear()
            actor.reports.clear()
        env.events.clear()
        env._refresh_local()

    def wait(self, env):
        return env.step({i: 0 for i in env.ready()})

    def relay_scenario(self, protocol="local"):
        env = Env(51, agents=3, communication=protocol, trace=True)
        self.setup_nodes(env, [1, 0, 2])
        env.step({0: 1, 1: 0, 2: 1})
        self.wait(env)
        self.wait(env)
        self.assertEqual(env.tick, 3)
        self.assertEqual(env.ready(), [0, 1])
        env.step({0: 8, 1: 0})
        return env

    def place_input(self, env, node, kind, quantity=1):
        env._depot[kind] -= quantity
        env._stocks[node][kind] += quantity
        env._refresh_local()

    def check_accounts(self, env):
        result = env.metrics()
        for key in ("conservation_residual_A", "conservation_residual_B", "demand_residual"):
            self.assertEqual(result[key], 0, (key, result))
        return result

    def test_remote_demand_and_material_are_private(self):
        env = Env(7, agents=1)
        before = env.obs(0)
        env._stocks[1] = [5, 4]
        env._orders[0].remaining = 1
        env._orders[0].kind = 1 - env._orders[0].kind
        self.assertEqual(before, env.obs(0))
        self.assertEqual(mask(before), mask(env.obs(0)))
        self.assertEqual(before[F["workshop_1_known"]], 0)

    def test_actor_in_transit_cannot_watch_departure_workers(self):
        env = Env(7, agents=2)
        self.setup_nodes(env, [0, 0])
        env.step({0: 2, 1: 0})
        before = env.obs(0)
        env._agents[1].task = "WORK"
        self.assertEqual(before, env.obs(0))
        self.assertEqual(before[F["local_peers"]], 0)
        self.assertEqual(before[F["local_workers"]], 0)

    def test_masks_prune_known_impossibilities_only(self):
        env = Env(7, agents=1)
        self.assertTrue(mask(env.obs(0))[4])
        self.assertFalse(mask(env.obs(0))[7])
        env._depot[0] = 0
        env._refresh_local()
        self.assertFalse(mask(env.obs(0))[4])
        self.setup_nodes(env, [1])
        self.assertFalse(mask(env.obs(0))[7])
        order = next(o for o in env._orders if o.node == 1)
        self.place_input(env, 1, order.kind)
        self.assertTrue(mask(env.obs(0))[7])

    def test_invalid_simultaneous_actions_rejected_atomically(self):
        env = Env(2, agents=2)
        self.setup_nodes(env, [0, 0])
        before = copy.deepcopy(env.__dict__)
        with self.assertRaises(ValueError):
            env.step({0: 4, 1: 7})
        self.assertEqual(before, env.__dict__)
        with self.assertRaises(ValueError):
            env.step({0: 4})
        self.assertEqual(before, env.__dict__)

    def test_travel_duration_and_loaded_empty_counters(self):
        env = Env(1, agents=1)
        env.step({0: 4})
        env.step({0: 2})
        self.assertNotIn(0, env.ready())
        self.wait(env)
        self.wait(env)
        self.assertEqual(env._agents[0].node, 1)
        self.assertEqual(env.tick, 1 + abs(COORDINATES[1]))
        self.assertEqual(env.metrics()["loaded_trips"], 1)
        self.assertEqual(env.metrics()["loaded_travel_ticks"], 3)
        env.step({0: 6})
        env.step({0: 1})
        self.wait(env)
        self.wait(env)
        self.assertEqual(env.metrics()["empty_travel_ticks"], 3)
        self.check_accounts(env)

    def test_reservation_at_horizon_preserves_input_and_order(self):
        env = Env(11, agents=1, horizon=1)
        self.setup_nodes(env, [1])
        order = next(o for o in env._orders if o.node == 1)
        self.place_input(env, 1, order.kind)
        reward, _, done = env.step({0: 7})
        self.assertTrue(done)
        self.assertEqual(reward, 0)
        result = self.check_accounts(env)
        self.assertEqual(result["demand_reserved"], 1)
        self.assertEqual(result["work_in_progress_A"] + result["work_in_progress_B"], 1)
        self.assertEqual(result["produced"], 0)

    def test_competing_workers_cannot_duplicate_reservation(self):
        env = Env(11, agents=2)
        self.setup_nodes(env, [1, 1])
        order = next(o for o in env._orders if o.node == 1)
        removed = order.remaining - 1
        order.remaining = 1
        env._counters["demand_issued"] -= removed
        self.place_input(env, 1, order.kind, 2)
        env.step({0: 7, 1: 7})
        self.assertEqual(env.metrics()["work_started"], 1)
        self.assertEqual(env.metrics()["work_denials"], 1)
        self.check_accounts(env)
        reward, _, _ = self.wait(env)
        self.assertEqual(reward, 1)
        self.assertEqual(self.check_accounts(env)["produced"], 1)

    def test_reserved_work_can_finish_after_deadline(self):
        env = Env(11, agents=1)
        self.setup_nodes(env, [1])
        order = next(o for o in env._orders if o.node == 1)
        order.deadline = 1
        original = order.remaining
        self.place_input(env, 1, order.kind)
        env.step({0: 7})
        self.assertEqual(env.metrics()["demand_expired"], original - 1)
        self.check_accounts(env)
        reward, _, _ = self.wait(env)
        self.assertEqual(reward, 1)
        self.assertEqual(self.check_accounts(env)["late_completed"], 1)

    def test_expired_orders_do_not_delete_unused_material(self):
        env = Env(9, agents=1)
        self.place_input(env, 1, 0, 2)
        for _ in range(PERIOD + 1):
            self.wait(env)
        self.assertGreater(env.metrics()["demand_expired"], 0)
        self.assertEqual(env._stocks[1][0], 2)
        self.assertGreater(env.metrics()["demand_issued"], 8)
        self.check_accounts(env)

    def test_shutdown_suppresses_arrivals_and_drains_old_orders(self):
        env = Env(9, agents=1, horizon=120, demand="shutdown", trace=True)
        while not env.done:
            self.wait(env)
            if env.tick >= env.quiet_after:
                self.assertEqual(env.metrics()["demand_pending"], 0)
        arrivals = [e for e in env.events if e["event"] == "ORDER_ISSUED"]
        self.assertTrue(all(e["tick"] < env.shutdown_tick for e in arrivals))
        result = self.check_accounts(env)
        self.assertEqual(result["demand_issued"], result["demand_expired"])

    def test_report_physical_handoff_preserves_original_witness(self):
        env = self.relay_scenario()
        first = env._agents[1].reports[1]
        self.assertEqual(first.evidence.observer, 0)
        self.assertEqual(first.evidence.observed_tick, 0)
        self.assertEqual(first.origin, "REPORT")
        self.assertNotIn(1, env._agents[2].reports)
        env.step({0: 0, 1: 8, 2: 0})
        second = env._agents[2].reports[1]
        self.assertEqual(second.evidence, first.evidence)
        self.assertEqual(second.route, (0, 1, 2))
        self.assertEqual(second.sender, 1)
        self.assertEqual(env.metrics()["forwarded"], 1)
        trace = [e for e in env.events if e["event"] == "REPORT_DELIVERED" and e["recipient"] == 2][-1]
        self.assertEqual(trace["parent_message_id"], first.message_id)

    def test_delivery_can_reach_busy_work_without_interrupting_it(self):
        env = Env(51, agents=3, trace=True)
        self.setup_nodes(env, [1, 2, 2])
        # Source witness travels 7 ticks from workshop1 to workshop2.
        env.step({0: 3, 1: 0, 2: 0})
        while env._agents[0].task:
            self.wait(env)
        order = next(o for o in env._orders if o.node == 2)
        self.place_input(env, 2, order.kind)
        env.step({0: 0, 1: 7, 2: 0})
        self.assertEqual(env._agents[1].task, "WORK")
        before = env._agents[1].reservation
        env.step({0: 8, 2: 0})
        self.assertIn(1, env._agents[1].reports)
        self.assertEqual(env.metrics()["produced"], 1)
        receipt = next(e for e in env.events if e["event"] == "REPORT_DELIVERED" and e["recipient"] == 1)
        exposures = [e for e in env.events if e["event"] == "REPORT_POLICY_INPUT" and e["citizen"] == 1]
        self.assertEqual(exposures, [])
        self.assertIsNotNone(before)
        self.wait(env)
        exposures = [e for e in env.events if e["event"] == "REPORT_POLICY_INPUT" and e["citizen"] == 1]
        self.assertGreater(exposures[0]["tick"], receipt["tick"])

    def test_information_carriage_links_real_trip_once(self):
        for loaded in (False, True):
            env = Env(51, agents=3, trace=True)
            self.setup_nodes(env, [1, 0, 2])
            if loaded:
                env._agents[0].cargo = 0
                env._depot[0] -= 1
                env._refresh_local()
            env.step({0: 1, 1: 0, 2: 1})
            self.wait(env)
            self.wait(env)
            env.step({0: 8, 1: 0})
            key = "loaded_trips_with_report_delivery" if loaded else "empty_trips_with_report_delivery"
            self.assertEqual(env.metrics()[key], 1)
            # Same observation may reach a newly encountered peer without
            # counting the same physical journey twice.
            env.step({0: 8, 1: 0, 2: 0})
            self.assertEqual(env.metrics()[key], 1)
            receipts = [e for e in env.events if e["event"] == "REPORT_DELIVERED"]
            trip_ids = {e["carrying_trip_id"] for e in receipts}
            self.assertEqual(trip_ids, {env._agents[0].last_trip["trip_id"]})
            self.check_accounts(env)

    def test_drop_surplus_is_descriptive_and_conserves_goods(self):
        env = Env(11, agents=1)
        self.setup_nodes(env, [1])
        kind = 1 - next(o.kind for o in env._orders if o.node == 1)
        env._agents[0].cargo = kind
        env._depot[kind] -= 1
        env._refresh_local()
        reward, _, _ = env.step({0: 6})
        self.assertEqual(reward, 0)
        self.assertEqual(env.metrics()["drops_without_current_need"], 1)
        self.assertEqual(env._stocks[1][kind], 1)
        self.check_accounts(env)

    def test_blocked_unread_and_no_relay_conditions(self):
        blocked = self.relay_scenario("no_messages")
        self.assertEqual(blocked.metrics()["delivered"], 0)
        self.assertGreater(blocked.metrics()["blocked"], 0)
        unread = self.relay_scenario("unread")
        self.assertIn(1, unread._agents[1].reports)
        self.assertEqual(unread.obs(1)[F["workshop_1_known"]], 0)
        unread.step({0: 0, 1: 8, 2: 0})
        self.assertEqual(unread.metrics()["read_report_inputs"], 0)
        self.assertEqual(unread.metrics()["forwarded"], 1)
        no_relay = self.relay_scenario("no_relay")
        self.assertEqual(no_relay.obs(1)[F["workshop_1_report"]], 1)
        self.assertFalse(mask(no_relay.obs(1))[8])

    def test_old_report_expiry_and_duplicate_preserve_age(self):
        env = self.relay_scenario()
        entry = env._agents[1].reports[1]
        self.assertFalse(env._admit(1, 0, env._agents[0].direct[1], "duplicate"))
        self.assertEqual(env._agents[1].reports[1], entry)
        while env.tick <= entry.evidence.observed_tick + TTL:
            self.wait(env)
        self.assertNotIn(1, env._agents[1].reports)
        self.assertEqual(env.metrics()["produced"], 0)

    def test_same_tick_receipt_cannot_be_forwarded(self):
        env = Env(51, agents=3, trace=True)
        self.setup_nodes(env, [1, 2, 0])
        env.step({0: 1, 1: 1, 2: 0})
        while len(env.ready()) < 3:
            self.wait(env)
        env.step({0: 8, 1: 8, 2: 0})
        self.assertEqual(env.metrics()["forwarded"], 0)
        sent = [e for e in env.events if e["event"] == "REPORT_SENT"]
        self.assertEqual({e["original_observer"] for e in sent}, {0, 1})

    def test_treatments_and_scopes_preserve_physics(self):
        worlds = [Env(23, communication=p, run_id=f"fixture:{p}") for p in PROTOCOLS]
        for other in worlds[1:]:
            self.assertEqual(worlds[0]._schedule, other._schedule)
            self.assertEqual(worlds[0]._priorities, other._priorities)
            self.assertEqual(worlds[0].initial_nodes, other.initial_nodes)
        a, b = Env(23, trace=True, run_id="scope:a"), Env(23, trace=True, run_id="scope:b")
        self.assertEqual([a.obs(i) for i in a.ready()], [b.obs(i) for i in b.ready()])
        self.assertNotEqual(a.events[0]["order_id"], b.events[0]["order_id"])
        self.assertEqual(a.metrics(), b.metrics())

    def test_random_physical_and_demand_conservation_each_tick(self):
        for communication in PROTOCOLS:
            for demand in DEMAND_REGIMES:
                env, rng = Env(103, horizon=120, communication=communication, demand=demand), random.Random(9)
                reward = 0
                while not env.done:
                    actions = {i: rng.choice([a for a, ok in enumerate(mask(env.obs(i))) if ok]) for i in env.ready()}
                    colony, personal, _ = env.step(actions)
                    reward += colony
                    self.assertTrue(all(x <= 0 for x in personal))
                    self.check_accounts(env)
                self.assertEqual(reward, env.metrics()["produced"])
                for key in ("produced", "attempts", "work_ticks", "travel_ticks"):
                    self.assertEqual(env.metrics()[key], sum(env.metrics()["phase_counts"][p][key] for p in ("early", "late")))

    def test_observation_only_script_produces_without_assigned_roles(self):
        env = Env(51)
        while not env.done:
            env.step({i: scripted_local(env.obs(i)) for i in env.ready()})
        result = self.check_accounts(env)
        self.assertGreater(result["produced"], 0)
        self.assertGreater(result["demand_issued"], 10)
        self.assertEqual(result["minecraft_worlds"], 0)
        self.assertNotIn("agent_id", F)
        self.assertNotIn("role", F)


if __name__ == "__main__":
    unittest.main()
