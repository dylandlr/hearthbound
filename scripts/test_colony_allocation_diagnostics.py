"""Analytic return-backup and replay-boundary checks; no learning result claimed."""
import copy
import hashlib
import random
import unittest
from unittest import mock

import numpy as np

from colony_task_env import Env, mask
from train_colony_task_allocation import GAMMA, Network, stable_seed
from colony_allocation_diagnostics import (greedy_backup, collect_corpus, train_fixed,
                                          evaluate, summarize)


def observation(time_remaining):
    values = list(Env(3401, horizon=10).obs(0))
    values[0] = time_remaining
    return tuple(values)


def trajectory():
    """Three legal inspection labels with independently chosen option durations."""
    states = [observation(x) for x in (1.0, .8, .5, .4)]
    durations = (2, 3, 1)
    rewards = (1., 2., 4.)
    starts = (0, 2, 5)
    return [dict(agent=0, episode=7, start_tick=starts[i], observation=states[i],
                 action=i + 1, discounted_reward=rewards[i],
                 next_observation=states[i + 1], duration=durations[i],
                 terminal=i == 2, next_index=None if i == 2 else i + 1)
            for i in range(3)]


class RecordedGreedy:
    def __init__(self, records, overrides=None):
        self.by_state = {tuple(r['observation']): r['action'] for r in records}
        self.by_state.update(overrides or {})
        self.calls = []

    def greedy(self, obs):
        self.calls.append(tuple(obs))
        return self.by_state[tuple(obs)]


class BackupTests(unittest.TestCase):
    def test_all_greedy_rewards_use_elapsed_ticks_not_option_count(self):
        records = trajectory()
        result = greedy_backup(records, 0, RecordedGreedy(records), 5)
        self.assertAlmostEqual(result['discounted_reward'], 1 + GAMMA ** 2 * 2 + GAMMA ** 5 * 4)
        self.assertEqual(result['duration'], 6)
        self.assertEqual(result['backup_depth'], 3)
        self.assertTrue(result['terminal'])
        self.assertEqual(tuple(result['next_observation']), records[2]['next_observation'])

    def test_nongreedy_successor_is_cut_before_its_reward(self):
        records = trajectory()
        records[1]['discounted_reward'] = 1e8
        model = RecordedGreedy(records, {records[1]['observation']: 4})
        result = greedy_backup(records, 0, model, 5)
        self.assertEqual(result['discounted_reward'], 1.)
        self.assertEqual(result['duration'], 2)
        self.assertEqual(result['backup_depth'], 1)
        self.assertFalse(result['terminal'])
        self.assertEqual(tuple(result['next_observation']), records[1]['observation'])
        self.assertTrue(result['cut_reason'])

    def test_cut_after_one_greedy_successor_preserves_partial_return(self):
        records = trajectory()
        model = RecordedGreedy(records, {records[2]['observation']: 4})
        result = greedy_backup(records, 0, model, 5)
        self.assertAlmostEqual(result['discounted_reward'], 1 + GAMMA ** 2 * 2)
        self.assertEqual(result['duration'], 5)
        self.assertEqual(result['backup_depth'], 2)
        self.assertFalse(result['terminal'])
        self.assertEqual(tuple(result['next_observation']), records[2]['observation'])

    def test_depth_cap_returns_bootstrap_at_next_state(self):
        records = trajectory()
        result = greedy_backup(records, 0, RecordedGreedy(records), 2)
        self.assertAlmostEqual(result['discounted_reward'], 1 + GAMMA ** 2 * 2)
        self.assertEqual(result['duration'], 5)
        self.assertEqual(result['backup_depth'], 2)
        self.assertFalse(result['terminal'])
        self.assertEqual(tuple(result['next_observation']), records[1]['next_observation'])

    def test_terminal_does_not_consult_a_later_action(self):
        records = trajectory()
        class NoFuture:
            def greedy(self, obs):
                raise AssertionError('Terminal transition must not inspect a future action')
        result = greedy_backup(records, 2, NoFuture(), 5)
        self.assertEqual(result['discounted_reward'], 4.)
        self.assertEqual(result['duration'], 1)
        self.assertEqual(result['backup_depth'], 1)
        self.assertTrue(result['terminal'])

    def test_one_step_is_the_original_transition(self):
        records = trajectory()
        class NoFuture:
            def greedy(self, obs):
                raise AssertionError('One-step backup must not read a successor action')
        result = greedy_backup(records, 0, NoFuture(), 1)
        for key in ('observation', 'action', 'discounted_reward', 'next_observation', 'duration', 'terminal'):
            self.assertEqual(result[key], records[0][key])
        self.assertEqual(result['backup_depth'], 1)

    def test_backup_does_not_mutate_frozen_corpus(self):
        records = trajectory()
        before = copy.deepcopy(records)
        greedy_backup(records, 0, RecordedGreedy(records), 5)
        self.assertEqual(records, before)

    def test_invalid_window_start_and_depth_rejected(self):
        records = trajectory()
        for start, depth in ((-1, 5), (len(records), 5), (0, 0), (0, -1)):
            with self.subTest(start=start, depth=depth), self.assertRaises((ValueError, AssertionError)):
                greedy_backup(records, start, RecordedGreedy(records), depth)

    def test_invalid_successor_indices_rejected(self):
        for pointer in (-1, 99, None):
            records = trajectory()
            records[0]['next_index'] = pointer
            with self.subTest(pointer=pointer), self.assertRaises((ValueError, AssertionError)):
                greedy_backup(records, 0, RecordedGreedy(records), 5)

    def test_cross_agent_and_cross_episode_returns_rejected(self):
        for field, value in (('agent', 1), ('episode', 8)):
            records = trajectory()
            records[1][field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, AssertionError)):
                greedy_backup(records, 0, RecordedGreedy(records), 5)

    def test_tick_and_observation_discontinuities_rejected(self):
        for field, value in (('start_tick', 3), ('observation', observation(.7))):
            records = trajectory()
            records[1][field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, AssertionError)):
                greedy_backup(records, 0, RecordedGreedy(records), 5)

    def test_collected_corpus_has_same_agent_contiguous_windows(self):
        records, metadata = collect_corpus(7101, 3, horizon=16, agents=2)
        self.assertTrue(records)
        self.assertTrue(metadata)
        terminal_counts = {}
        for index, row in enumerate(records):
            self.assertEqual(len(row['observation']), 38)
            self.assertTrue(mask(row['observation'])[row['action']])
            self.assertGreater(row['duration'], 0)
            key = (row['episode'], row['agent'])
            terminal_counts.setdefault(key, 0)
            if row['terminal']:
                terminal_counts[key] += 1
                self.assertIsNone(row['next_index'])
                continue
            successor = row['next_index']
            self.assertIsInstance(successor, int)
            self.assertGreaterEqual(successor, 0)
            self.assertLess(successor, len(records))
            following = records[successor]
            self.assertEqual((following['episode'], following['agent']), key)
            self.assertEqual(following['start_tick'], row['start_tick'] + row['duration'])
            self.assertEqual(tuple(following['observation']), tuple(row['next_observation']))
        self.assertEqual(len(terminal_counts), 6)
        self.assertTrue(all(count == 1 for count in terminal_counts.values()))


class DiagnosticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed, cls.updates = 7101, 6
        cls.records, _ = collect_corpus(cls.seed, 4, horizon=16, agents=2)
        cls.original_records = copy.deepcopy(cls.records)
        indices = {(row['episode'], row['agent'], row['start_tick']): index
                   for index, row in enumerate(cls.records)}
        cls.calls = {}
        original_update = Network.update

        def traced_update(model, batch, target, rate=0.001):
            calls = cls.calls.setdefault(id(model), [])
            calls.append(dict(before=model.digest(), target=target.digest(),
                              starts=[indices[(row['episode'], row['agent'], row['start_tick'])]
                                      for row in batch],
                              depths=[row['backup_depth'] for row in batch]))
            return original_update(model, batch, target, rate=rate)

        with mock.patch.object(Network, 'update', new=traced_update):
            cls.models, cls.initial, cls.stats = train_fixed(cls.seed, cls.records, cls.updates)

    def test_matched_training_uses_actual_same_initialization_and_sample_order(self):
        initial_hash = Network(self.seed).digest()
        self.assertEqual(self.initial.digest(), initial_hash)
        self.assertEqual(self.initial.updates, 0)
        self.assertEqual(self.records, self.original_records)
        rng = random.Random(stable_seed('diagnostic-minibatches', self.seed))
        expected_starts = [rng.sample(range(len(self.records)), 32)
                           for _ in range(self.updates)]
        expected_hash = hashlib.sha256(''.join(','.join(map(str, starts)) + '\n'
                                                for starts in expected_starts).encode()).hexdigest()
        for name, model in self.models.items():
            with self.subTest(arm=name):
                calls, stats = self.calls[id(model)], self.stats[name]
                self.assertEqual(calls[0]['before'], initial_hash)
                self.assertEqual([call['starts'] for call in calls], expected_starts)
                self.assertTrue(all(call['target'] == initial_hash for call in calls))
                self.assertEqual(len(calls), self.updates)
                self.assertEqual(model.updates, self.updates)
                self.assertEqual(stats['optimizer_updates'], self.updates)
                self.assertEqual(stats['sampled_starts'], 32 * self.updates)
                self.assertEqual(stats['sampled_start_order_sha256'], expected_hash)
                self.assertEqual(stats['initial_parameter_sha256'], initial_hash)
                self.assertEqual(stats['parameter_sha256'], model.digest())
                self.assertNotEqual(model.digest(), initial_hash)
                self.assertTrue(all(1 <= depth <= (1 if name == 'offline_td' else 5)
                                    for call in calls for depth in call['depths']))
        td = self.stats['offline_td']
        self.assertEqual(td['backup_depth_histogram'], {1: 32 * self.updates})
        self.assertEqual(td['mean_backup_options'], 1)
        self.assertEqual(td['fraction_multistep'], 0)

    def test_frozen_full_and_pruned_evaluation_preserves_resources_and_time(self):
        # A constant inspection preference guarantees this check exercises the alias.
        inspect_fixture = Network(81)
        for value in inspect_fixture.parameters.values():
            value.fill(0)
        inspect_fixture.parameters['b2'][1] = 2
        inspect_fixture.parameters['b2'][0] = 1
        models = dict(self.models, inspect_fixture=inspect_fixture)
        before = {name: (model.digest(), model.updates, copy.deepcopy(model.m),
                         copy.deepcopy(model.v)) for name, model in models.items()}
        worlds, horizon = (3301, 3302), 16
        rows, examples = evaluate(models, worlds, ['standard'], agents=2, horizon=horizon)
        self.assertEqual(len(rows), (len(models) + 3) * 2 * len(worlds))
        for name, model in models.items():
            self.assertEqual((model.digest(), model.updates), before[name][:2])
            for parameter in model.parameters:
                np.testing.assert_array_equal(model.m[parameter], before[name][2][parameter])
                np.testing.assert_array_equal(model.v[parameter], before[name][3][parameter])
        for row in rows:
            with self.subTest(policy=row['policy'], pruned=row['pruned'], world=row['world_seed']):
                self.assertEqual(row['tick'], horizon)
                self.assertEqual(row['horizon'], horizon)
                self.assertEqual(row['minecraft_worlds'], 0)
                self.assertEqual(row['colony_reward'], row['produced'])
                for ingredient in ('A', 'B'):
                    self.assertEqual(row['conservation_residual_' + ingredient], 0)
                    self.assertEqual(row['initial_' + ingredient], row['source_' + ingredient]
                                     + row['hub_' + ingredient] + row['transit_' + ingredient]
                                     + row['produced'])
                if row['pruned']:
                    self.assertEqual(row['same_site_inspections'], 0)
        full_fixture = [row for row in rows
                        if row['policy'] == 'inspect_fixture' and not row['pruned']]
        self.assertTrue(all(row['same_site_inspections'] > 0 for row in full_fixture))
        for example in examples.values():
            trace = example['action_trace']
            for agent in range(2):
                starts = [event['tick'] for event in trace if event['agent'] == agent]
                self.assertEqual(starts[0], 0)
                durations = [end - start for start, end in zip(starts, starts[1:] + [horizon])]
                self.assertTrue(all(duration > 0 for duration in durations))
                self.assertEqual(sum(durations), horizon)

    def test_summary_uses_world_paired_differences_within_each_training_seed(self):
        seeds, worlds = (7, 11), (101, 102)
        differences = ((1, 3), (5, 7))
        policies = ('offline_td', 'offline_greedy5', 'random', 'legacy_online')
        rows = []
        for si, seed in enumerate(seeds):
            for wi, world in enumerate(worlds):
                baseline = (10, 20, 100, 200)[si * 2 + wi]
                for policy in policies:
                    for pruned in (False, True):
                        produced = baseline + (differences[si][wi] if policy == 'offline_greedy5' else 0)
                        if pruned:
                            produced += {'offline_td': 3, 'offline_greedy5': 5,
                                         'random': -2, 'legacy_online': 4}[policy]
                        rows.append(dict(training_seed=seed, world_seed=world, regime='standard',
                                         policy=policy, pruned=pruned, produced=produced,
                                         same_site_inspections=0, wait_decisions=0,
                                         totaltravel=0, denials=0))
        expected = {'alias_legacy_primary': [[4, 4], [4, 4]],
                    'credit_full': [[1, 3], [5, 7]],
                    'credit_pruned_secondary': [[3, 5], [7, 9]],
                    'alias_offline_td': [[3, 3], [3, 3]],
                    'alias_offline_greedy5': [[5, 5], [5, 5]],
                    'alias_random': [[-2, -2], [-2, -2]]}
        # Isolate matrix construction from the separately implemented resampling routine.
        with mock.patch('colony_allocation_diagnostics.base.crossed_interval',
                        side_effect=lambda matrix: [float(np.min(matrix)), float(np.max(matrix))]) as interval:
            result = summarize(list(reversed(rows)), seeds, worlds)['standard']
        self.assertEqual(interval.call_count, len(expected))
        self.assertEqual(set(result['effects']), set(expected))
        for (label, effect), call in zip(result['effects'].items(), interval.call_args_list):
            matrix = expected[label]
            self.assertEqual(call.args[0], matrix)
            self.assertEqual(effect['mean_products_difference'], float(np.mean(matrix)))
            self.assertEqual(effect['per_training_seed_difference'],
                             [float(np.mean(row)) for row in matrix])
            self.assertEqual(effect['crossed_bootstrap_95_percent_interval'],
                             [float(np.min(matrix)), float(np.max(matrix))])


if __name__ == '__main__':
    unittest.main(verbosity=2)
