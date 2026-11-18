"""Adversarial restart-harness checks; no Minecraft execution is simulated or claimed."""
import json
import unittest

from rcon_pickup_belief_restart import (
    ORIGINAL_PAUSE_REASON, RESTORED_PAUSE_REASON, outer_error_span,
    verify_restored_haul, wait_for_restart_pause,
)


class RestartHarnessTests(unittest.TestCase):
    def setUp(self):
        self.before = ('{phase: 3, jobId: [I; 1, 2, 3, 4], source: 12L, destination: 34L, '
                       'reportPolicyDispatch.v1: {job: [I; 1, 2, 3, 4], reportId: "fact-a"}, '
                       'error: ' + json.dumps(ORIGINAL_PAUSE_REASON) + ', assignedTick: 5L}')
        self.after = self.before.replace(json.dumps(ORIGINAL_PAUSE_REASON),
                                         json.dumps(RESTORED_PAUSE_REASON))

    def test_expected_diagnostic_transition(self):
        verify_restored_haul(self.before, self.after)

    def test_identity_state_and_cargo_changes_rejected(self):
        mutations = (
            self.after.replace('phase: 3', 'phase: 0'),
            self.after.replace('1, 2, 3, 4', '1, 2, 3, 9', 1),
            self.after.replace('source: 12L', 'source: 13L'),
            self.after.replace('destination: 34L', 'destination: 35L'),
            self.after.replace('assignedTick: 5L', 'assignedTick: 6L'),
            self.after.replace('reportId: "fact-a"', 'reportId: "fact-b"'),
            self.after.replace('phase: 3', 'phase: 3, cargo: {Count: 1b}'),
        )
        for mutated in mutations:
            with self.subTest(mutated=mutated), self.assertRaises(AssertionError):
                verify_restored_haul(self.before, mutated)

    def test_unexpected_or_unchanged_reason_rejected(self):
        for after in (self.before, self.after.replace(RESTORED_PAUSE_REASON, 'Other failure')):
            with self.subTest(after=after), self.assertRaises(AssertionError):
                verify_restored_haul(self.before, after)

    def test_missing_duplicate_or_nonstr_error_rejected(self):
        for text in ('{phase: 3}', '{error: "one", error: "two"}',
                     '{error: "one", "error": "two"}', '{error: 3}'):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                outer_error_span(text)

    def test_nested_error_does_not_authorize_outer_transition(self):
        nested = '{report: {error: ' + json.dumps(RESTORED_PAUSE_REASON) + '}, phase: 3}'
        with self.assertRaises(AssertionError):
            outer_error_span(nested)
        with self.assertRaises(AssertionError):
            verify_restored_haul(self.before, nested)

    def test_nested_matching_text_and_escapes_are_preserved(self):
        payload = json.dumps('quoted "error: x", brace }, comma, backslash \\')
        before = self.before.replace('phase: 3',
            'phase: 3, nested: {error: "No wheat available", text: ' + payload + '}')
        start, end, _ = outer_error_span(before)
        after = before[:start] + json.dumps(RESTORED_PAUSE_REASON) + before[end:]
        verify_restored_haul(before, after)
        wrong = after.replace('nested: {error: "No wheat available"',
                               'nested: {error: "changed"')
        with self.assertRaises(AssertionError):
            verify_restored_haul(before, wrong)

    def test_malformed_structure_rejected(self):
        for text in ('{error: "unterminated}', '{x: [1, 2}, error: "x"}',
                     '{x: {a: 1], error: "x"}'):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                outer_error_span(text)

    def test_waits_for_exact_gate_and_correct_job(self):
        expected = ('Paused: ' + RESTORED_PAUSE_REASON).replace(' ', '_')
        responses = [
            'job=task-a status=INCOMPLETE executor_state=Paused:_No_wheat_available',
            'job=other status=INCOMPLETE executor_state=' + expected,
            'job=task-a status=INCOMPLETE executor_state=' + expected,
        ]
        class Replies:
            def run(self, command):
                return responses.pop(0)
        ticks = iter(range(10))
        receipt = wait_for_restart_pause(Replies(), 'task-a', timeout=5,
                                        sleep=lambda _: None, clock=lambda: next(ticks))
        self.assertIn('job=task-a', receipt)
        self.assertEqual(responses, [])

    def test_wait_timeout_does_not_accept_generic_pause(self):
        class Replies:
            def run(self, command):
                return 'job=task-a status=INCOMPLETE executor_state=Paused:_No_wheat_available'
        ticks = iter(range(10))
        with self.assertRaises(AssertionError):
            wait_for_restart_pause(Replies(), 'task-a', timeout=2,
                                   sleep=lambda _: None, clock=lambda: next(ticks))


if __name__ == '__main__':
    unittest.main(verbosity=2)
