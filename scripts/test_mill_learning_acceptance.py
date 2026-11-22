import unittest

from mill_learning_acceptance import require_denial, require_replay


class LearningOracleTest(unittest.TestCase):
    def setUp(self):
        self.proposal = ("MILL_OUTCOME_PROPOSAL status=PROPOSED world=w job=j citizen=c "
                         "physical_evidence_id=p assigned_tick=10 process_finish_tick=30")
        target = .5 * .999 ** 20
        self.response = ("MILL_LEARNING_SHADOW status=REPLAYED "
                         "event=hearthbound:mill:v1:w:minecraft:overworld:j citizen=c "
                         "physical_evidence_id=p samples=1 updates=1 duration_ticks=20 "
                         f"personal_milli=500 target={target} q_before=0.0 q_after={.25 * target} "
                         "alpha=0.25 gamma_per_tick=0.999 replay_from_zero=true "
                         "model_persisted=false success_only=true shadow_learning_authorized=true "
                         "policy_control=false reward_authorized=false learning_authorized=false "
                         "NO_RESEARCH_CREDIT")
        self.denied = ("MILL_LEARNING_SHADOW status=DENIED reason=EVIDENCE_REVOKED "
                       "shadow_learning_authorized=false updates=0 policy_control=false "
                       "reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT")

    def test_numeric_update(self):
        require_replay(self.response, self.proposal)

    def test_denial(self):
        require_denial(self.denied, "EVIDENCE_REVOKED")

    def test_fake_or_nonfinite_update(self):
        for value in ("0", "nan", "inf", "0.5"):
            with self.subTest(value=value), self.assertRaises(AssertionError):
                import re
                require_replay(re.sub(r"q_after=\S+", "q_after=" + value, self.response), self.proposal)

    def test_wrong_evidence_and_boundaries(self):
        for old, new in (("physical_evidence_id=p", "physical_evidence_id=other"),
                         ("citizen=c", "citizen=other"), ("updates=1", "updates=2"),
                         ("duration_ticks=20", "duration_ticks=10"),
                         ("personal_milli=500", "personal_milli=1000"),
                         ("policy_control=false", "policy_control=true"),
                         ("world:j", "world:other")):
            with self.subTest(old=old), self.assertRaises(AssertionError):
                require_replay(self.response.replace(old, new), self.proposal)

    def test_denial_cannot_retain_value(self):
        with self.assertRaises(AssertionError):
            require_denial(self.denied + " q_after=0.1", "EVIDENCE_REVOKED")

    def test_denial_must_not_update(self):
        with self.assertRaises(AssertionError):
            require_denial(self.denied.replace("updates=0", "updates=1"), "EVIDENCE_REVOKED")


if __name__ == "__main__":
    unittest.main()
