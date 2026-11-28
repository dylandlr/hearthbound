"""Fixed scenario-v1 oracles, scoped binding, and Java/Python parity; no native effects."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

from event_scheduler import MAX_TICK, Scheduler
from event_scenarios import (Config, Position, Rule, Scenario, Scope, MAX_CONFIG_BYTES,
                             MAX_MANIFEST_BYTES, _draw)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/fixtures/event_scenarios"


def basic():
    return Config.from_bytes((FIXTURES / "basic.config").read_bytes())


def latent(scenario):
    return [(c.rule_id, c.ordinal, c.pair_id, c.kind, c.scope, c.targets, c.target_digest,
             c.onset, c.duration, c.intended_ppm) for c in scenario.choices]


def small_config(*, x=0, dimension="minecraft:overworld", onset_min=2, onset_max=2,
                 duration_min=1, duration_max=1, count=1):
    scope = Scope("plot", dimension, Position(x, 64, 0), Position(x, 64, 0), [Position(x, 64, 0)])
    rule = Rule("crop", "crop_failure", count, onset_min, onset_max, duration_min, duration_max,
                500000, 500000, 1, ["plot"])
    return Config([scope], [rule])


class ScenarioContracts(unittest.TestCase):
    def test_fixed_manifest_hashes_and_latent_choice_oracles(self):
        config = basic()
        self.assertEqual("00579fa97894a6759e7115109213e82bf0b4f3065105a4a0679337b3b53b9a78", config.digest)
        expected = {}
        for line in (FIXTURES / "latent-choices.tsv").read_text().splitlines():
            seed, rule, ordinal, scope, onset, duration, ppm, positions = line.split("\t")
            expected[(int(seed), rule, int(ordinal))] = (scope, int(onset), int(duration), int(ppm), positions)
        for line in (FIXTURES / "golden-index.tsv").read_text().splitlines():
            seed, mode, trial, filename, manifest_hash, schedule_hash, run_id = line.split("\t")
            with self.subTest(seed=seed, mode=mode):
                scenario = Scenario(config, int(seed), mode, trial)
                oracle = (FIXTURES / filename).read_bytes()
                self.assertEqual(manifest_hash, hashlib.sha256(oracle).hexdigest())
                self.assertEqual(oracle, scenario.manifest)
                self.assertEqual(manifest_hash, scenario.manifest_digest)
                self.assertEqual(schedule_hash, scenario.schedule.digest)
                self.assertEqual(run_id, scenario.journal_run_id)
                self.assertEqual(oracle, Scenario.from_manifest(oracle).manifest)
                for choice in scenario.choices:
                    positions = ";".join(f"{p.x},{p.y},{p.z}" for p in choice.targets)
                    self.assertEqual(expected[(int(seed), choice.rule_id, choice.ordinal)],
                                     (choice.scope.scope_id, choice.onset, choice.duration, choice.intended_ppm, positions))

    def test_paired_modes_retain_intended_choices_and_distinct_execution_plans(self):
        treatment = Scenario(basic(), 7, "treatment", "paired-treatment")
        sham = Scenario(basic(), 7, "sham", "paired-sham")
        control = Scenario(basic(), 7, "no_event", "paired-no-event")
        self.assertEqual(latent(treatment), latent(sham))
        self.assertEqual(latent(treatment), latent(control))
        self.assertTrue(all(c.effective_ppm == c.intended_ppm > 0 for c in treatment.choices))
        self.assertTrue(all(c.effective_ppm == 0 and c.event.severity == 0 for c in sham.choices))
        self.assertTrue(all(c.effective_ppm is None and c.event is None for c in control.choices))
        self.assertEqual(3, len(sham.schedule.events))
        self.assertFalse(control.schedule.events)
        self.assertEqual(3, len({s.manifest_digest for s in (treatment, sham, control)}))
        self.assertEqual(3, len({s.journal_run_id for s in (treatment, sham, control)}))
        self.assertFalse(set(e.event_id for e in treatment.schedule.events) & set(e.event_id for e in sham.schedule.events))

    def test_seed_repeatability_and_changed_seed_draws(self):
        a = Scenario(basic(), 0, "treatment", "trial")
        self.assertEqual(a.manifest, Scenario(basic(), 0, "treatment", "trial").manifest)
        b = Scenario(basic(), 7, "treatment", "trial")
        self.assertNotEqual([(c.onset, c.duration, c.targets) for c in a.choices],
                            [(c.onset, c.duration, c.targets) for c in b.choices])
        other_trial = Scenario(basic(), 0, "treatment", "other-trial")
        self.assertEqual(latent(a), latent(other_trial))
        self.assertNotEqual(a.journal_run_id, other_trial.journal_run_id)
        self.assertIn(b"TRIAL\tother-trial\n", other_trial.manifest)

    def test_input_order_invariance_and_deep_immutable_views(self):
        original = basic()
        scopes = [replace(s, targets=list(reversed(s.targets))) for s in reversed(original.scopes)]
        rules = [replace(r, scope_ids=list(reversed(r.scope_ids))) for r in reversed(original.rules)]
        config = Config(scopes, rules)
        self.assertEqual(original.canonical, config.canonical)
        self.assertEqual(Scenario(original, 7, "treatment", "t").manifest, Scenario(config, 7, "treatment", "t").manifest)
        scopes.clear(); rules.clear()
        self.assertEqual(2, len(config.scopes))
        targets = [Position(0, 64, 0)]
        scope = Scope("s", "minecraft:overworld", targets[0], targets[0], targets)
        targets.append(Position(1, 64, 0))
        self.assertEqual((Position(0, 64, 0),), scope.targets)
        for item, attribute, value in [(scope, "dimension", "minecraft:the_nether"), (config, "digest", "fake"),
                                        (Scenario(config, 0, "sham", "trial"), "trial_id", "changed")]:
            with self.assertRaises(FrozenInstanceError):
                setattr(item, attribute, value)

    def test_invalid_identity_kind_seed_mode_and_trial(self):
        config = small_config()
        for seed in (-1, MAX_TICK + 1, True, 1.0, "1"):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                Scenario(config, seed, "treatment", "trial")
        for mode in ("SHAM", "", None, 1):
            with self.assertRaises(ValueError):
                Scenario(config, 1, mode, "trial")
        for trial in ("a\nb", "bad:id", "é", "x" * 65, ""):
            with self.assertRaises(ValueError):
                Scenario(config, 1, "treatment", trial)
        for kind in ("specialist_loss", "communication_failure", "demand_change", "unknown"):
            with self.assertRaises(ValueError):
                replace(config.rules[0], kind=kind)
        with self.assertRaises(ValueError):
            replace(config.scopes[0], scope_id="scope:bad")

    def test_scope_coordinates_regions_and_target_validation(self):
        for coordinate in (True, 1.0, -(1 << 31) - 1, 1 << 31):
            with self.assertRaises(ValueError):
                Position(coordinate, 0, 0)
        p = Position(0, 64, 0)
        for dim in ("overworld", "Minecraft:overworld", "a:" + "b" * 127, "minecraft:over\nworld"):
            with self.assertRaises(ValueError):
                Scope("s", dim, p, p, [p])
        with self.assertRaises(ValueError):
            Scope("s", "minecraft:overworld", p, p, [p, p])
        with self.assertRaises(ValueError):
            Scope("s", "minecraft:overworld", p, p, [])
        with self.assertRaises(ValueError):
            Scope("s", "minecraft:overworld", p, p, [Position(1, 64, 0)])
        with self.assertRaises(ValueError):
            Scope("s", "minecraft:overworld", p, Position(256, 64, 0), [p])
        with self.assertRaises(ValueError):
            Scope("s", "minecraft:overworld", p, Position(-1, 64, 0), [p])
        extreme = Scope("edge", "minecraft:overworld", Position(-(1 << 31), (1 << 31) - 1, 0),
                        Position(-(1 << 31) + 1, (1 << 31) - 1, 0), [Position(-(1 << 31), (1 << 31) - 1, 0)])
        self.assertEqual(extreme, Config.from_bytes(Config([extreme], []).canonical).scopes[0])

    def test_range_validation_and_total_capacities(self):
        config = small_config(); rule = config.rules[0]
        for changes in ({"onset_min": -1}, {"onset_max": 1}, {"duration_min": 0}, {"duration_max": 0},
                        {"onset_max": MAX_TICK}, {"duration_max": MAX_TICK}, {"severity_min_ppm": -1},
                        {"severity_max_ppm": 1_000_001}, {"severity_min_ppm": 500001},
                        {"count": 0}, {"count": 4097}, {"count": True}, {"targets_per_event": 0},
                        {"scope_ids": []}, {"scope_ids": ["plot", "plot"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(rule, **changes)
        with self.assertRaises(ValueError):
            Config(config.scopes, [replace(rule, scope_ids=["unknown"])])
        with self.assertRaises(ValueError):
            Config(config.scopes, [replace(rule, targets_per_event=2)])
        with self.assertRaises(ValueError):
            Config(config.scopes * 2, [rule])
        with self.assertRaises(ValueError):
            Config(config.scopes, [rule, rule])
        with self.assertRaises(ValueError):
            Config(config.scopes, [replace(rule, count=4096), replace(rule, rule_id="other")])
        with self.assertRaises(ValueError):
            Config([replace(config.scopes[0], scope_id="s" + str(i)) for i in range(65)], [])
        with self.assertRaises(ValueError):
            Config(config.scopes, [replace(rule, rule_id="r" + str(i)) for i in range(65)])
        points = [Position(i, 64, 0) for i in range(17)]
        scope = Scope("plot", "minecraft:overworld", points[0], points[-1], points)
        with self.assertRaises(ValueError):
            Config([scope], [replace(rule, count=4096, targets_per_event=17)])

    def test_full_width_tick_ranges_seed_and_rejection_sampling(self):
        for config in (small_config(onset_min=0, onset_max=MAX_TICK - 1),
                       small_config(onset_min=0, onset_max=0, duration_min=1, duration_max=MAX_TICK)):
            scenario = Scenario(config, MAX_TICK, "treatment", "edge")
            c = scenario.choices[0]
            self.assertLessEqual(c.onset + c.duration, MAX_TICK)
            self.assertGreater(max(c.onset, c.duration), 1 << 32)
        exact = Scenario(small_config(onset_min=MAX_TICK - 1, onset_max=MAX_TICK - 1), MAX_TICK, "treatment", "edge")
        self.assertEqual(MAX_TICK, exact.choices[0].onset + exact.choices[0].duration)
        messages = []
        def reject_once(message):
            messages.append(message)
            return b"\xff" * 32 if len(messages) == 1 else b"\x00" * 32
        self.assertEqual(0, _draw("0" * 64, "r", 0, "onset", 3, reject_once))
        self.assertEqual(2, len(messages))
        self.assertTrue(messages[0].endswith(b"\n0\n"))
        self.assertTrue(messages[1].endswith(b"\n1\n"))
        self.assertEqual(MAX_TICK, _draw("0" * 64, "r", 0, "onset", 1 << 63, lambda _: b"\xff" * 32))
        for bound in (0, -1, (1 << 63) + 1, True):
            with self.assertRaises(ValueError):
                _draw("0" * 64, "r", 0, "x", bound)
        with self.assertRaises(ValueError):
            _draw("0" * 64, "r", 0, "x", 3, lambda _: b"\xff" * 32)
        with self.assertRaises(ValueError):
            _draw("0" * 64, "r", 0, "x", 3, lambda _: b"\x00")

    def test_maximum_event_count_and_target_selection_without_replacement(self):
        scenario = Scenario(small_config(count=4096), 0, "treatment", "capacity")
        self.assertEqual(4096, len(scenario.schedule.events))
        self.assertEqual(4096, len({choice.event.event_id for choice in scenario.choices}))
        points = [Position(i, 64, 0) for i in range(256)]
        scope = Scope("plot", "minecraft:overworld", points[0], points[-1], points)
        rule = replace(small_config().rules[0], targets_per_event=256)
        chosen = Scenario(Config([scope], [rule]), 7, "sham", "all-targets").choices[0]
        self.assertEqual(tuple(points), chosen.targets)
        self.assertEqual(256, len(set(chosen.targets)))

    def test_canonical_documents_reject_corruption_unknown_versions_and_reordering(self):
        config = basic().canonical
        for changed in (config[:-1], config + b"EXTRA\n", config.replace(b"config:v1", b"config:v2"),
                        config.replace(b"SCOPES\t2", b"SCOPES\t02"), config.replace(b"\n", b"\r\n"),
                        config.replace(b"BLOCK\t-2\t64\t0\nBLOCK\t-1\t64\t1", b"BLOCK\t-1\t64\t1\nBLOCK\t-2\t64\t0"),
                        config.replace(b"BLOCK\t-2", b"BLOCK\t-2147483649"), b"x" * (MAX_CONFIG_BYTES + 1)):
            with self.assertRaises(ValueError):
                Config.from_bytes(changed)
        scene = Scenario(basic(), 7, "treatment", "trial")
        for changed in (scene.manifest[:-1], scene.manifest + b"EXTRA\n", scene.manifest.replace(b"manifest:v1", b"manifest:v2"),
                        scene.manifest.replace(b"SEED\t7", b"SEED\t8"), scene.manifest.replace(b"TRIAL\ttrial", b"TRIAL\tother"),
                        scene.manifest.replace(b"TARGET\t10", b"TARGET\t99"), b"x" * (MAX_MANIFEST_BYTES + 1)):
            with self.assertRaises(ValueError):
                Scenario.from_manifest(changed)

    def test_scope_changes_bind_events_and_wrapper_reopen_including_empty_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("treatment", "no_event"):
                scenario = Scenario(small_config(), 0, mode, "trial")
                path = Path(temporary) / (mode + ".log")
                with scenario.create_scheduler(path, "world") as scheduler:
                    scheduler.poll(0)
                before = path.read_bytes()
                with scenario.open_scheduler(path, "world") as scheduler:
                    self.assertEqual(0, scheduler.cursor)
                alternatives = [Scenario(small_config(), 1, mode, "trial"), Scenario(small_config(), 0, mode, "other"),
                                Scenario(small_config(x=1), 0, mode, "trial"),
                                Scenario(small_config(dimension="minecraft:the_nether"), 0, mode, "trial"),
                                Scenario(small_config(), 0, "sham", "trial")]
                for other in alternatives:
                    self.assertNotEqual(scenario.manifest_digest, other.manifest_digest)
                    self.assertNotEqual(scenario.journal_run_id, other.journal_run_id)
                    with self.assertRaises((ValueError, OSError)):
                        other.open_scheduler(path, "world")
                with self.assertRaises((ValueError, OSError)):
                    scenario.open_scheduler(path, "foreign-world")
                with self.assertRaises((ValueError, OSError)):
                    Scheduler.open(path, scenario.schedule, "world", scenario.trial_id)
                self.assertEqual(before, path.read_bytes())
                if mode == "treatment":
                    self.assertNotEqual(scenario.schedule.digest, alternatives[2].schedule.digest)
                else:
                    self.assertEqual(scenario.schedule.digest, alternatives[2].schedule.digest)

    def test_wrapper_preserves_pending_reconciliation_and_exact_choice_lookup(self):
        scenario = Scenario(small_config(), 0, "treatment", "trial")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "journal"
            with scenario.create_scheduler(path, "world") as scheduler:
                pending = scheduler.poll(2)
                choice = scenario.event_choice(pending.transition.event_id)
                self.assertEqual(small_config().scopes[0], choice.scope)
            restored = Scenario.from_manifest(scenario.manifest)
            with restored.open_scheduler(path, "world") as scheduler:
                self.assertTrue(scheduler.pending.recovery_required)
                self.assertFalse(scheduler.pending.executable)
                with self.assertRaises(ValueError):
                    scheduler.acknowledge(pending.transition.transition_id, "APPLIED", "false-witness", 2)
                scheduler.reconcile(pending.transition.transition_id, "NOT_APPLIED", "synthetic-no-effect")
                self.assertEqual(1, scheduler.next_index)
            with self.assertRaises(ValueError):
                scenario.event_choice("unknown")
            other = Scenario(small_config(x=1), 0, "treatment", "trial")
            with self.assertRaises(ValueError):
                scenario.event_choice(other.schedule.events[0].event_id)


class ScenarioLanguageParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java_exe = shutil.which("java")
        if not cls.java_exe:
            raise RuntimeError("Java is required for scenario parity")
        cls.output = None
        cls.classpath = os.environ.get("HEARTHBOUND_EVENT_JAVA_CLASSPATH")
        if not cls.classpath:
            cls.output = tempfile.TemporaryDirectory(prefix="hearthbound-scenario-java-")
            cls.classpath = cls.output.name
            javac = shutil.which("javac")
            compiler = [javac] if javac else [cls.java_exe, "--module", "jdk.compiler/com.sun.tools.javac.Main"]
            sources = sorted((ROOT / "src/main/java/dev/hearthbound/experiment").glob("*.java"))
            sources += sorted((ROOT / "src/test/java/dev/hearthbound/experiment").glob("*.java"))
            subprocess.run(compiler + ["--release", "17", "-encoding", "UTF-8", "-d", cls.classpath]
                           + [str(p) for p in sources], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        if cls.output is not None:
            cls.output.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hearthbound-scenario-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)

    def java(self, *args, success=True):
        result = subprocess.run([self.java_exe, "-cp", self.classpath, "dev.hearthbound.experiment.EventScenariosCli",
                                 *map(str, args)], cwd=ROOT, capture_output=True, timeout=20)
        if success:
            self.assertEqual(0, result.returncode, result.stderr.decode(errors="replace"))
        else:
            self.assertNotEqual(0, result.returncode, result.stdout.decode(errors="replace"))
        return result.stdout

    def test_all_fixed_oracle_manifests_identical_across_languages(self):
        for line in (FIXTURES / "golden-index.tsv").read_text().splitlines():
            seed, mode, trial, filename, *_ = line.split("\t")
            oracle = (FIXTURES / filename).read_bytes()
            with self.subTest(seed=seed, mode=mode):
                self.assertEqual(oracle, self.java("generate", FIXTURES / "basic.config", seed, mode, trial))
                self.assertEqual(oracle, self.java("roundtrip", FIXTURES / filename))

    def test_full_width_ranges_and_coordinate_boundaries_match(self):
        edge_scope = Scope("plot", "minecraft:overworld", Position(-(1 << 31), (1 << 31) - 1, 0),
                           Position(-(1 << 31), (1 << 31) - 1, 0), [Position(-(1 << 31), (1 << 31) - 1, 0)])
        configs = [small_config(onset_min=0, onset_max=MAX_TICK - 1),
                   small_config(onset_min=0, onset_max=0, duration_max=MAX_TICK),
                   Config([edge_scope], small_config().rules), Config([], [])]
        for index, config in enumerate(configs):
            file = self.path / f"edge-{index}.config"; file.write_bytes(config.canonical)
            for mode in ("treatment", "sham", "no_event"):
                self.assertEqual(Scenario(config, MAX_TICK, mode, "edge").manifest,
                                 self.java("generate", file, MAX_TICK, mode, "edge"))

    def test_bidirectional_wrapper_journals_and_held_intent(self):
        scenario = Scenario(small_config(), 7, "treatment", "trial")
        manifest = self.path / "scenario.manifest"; manifest.write_bytes(scenario.manifest)
        py_path = self.path / "python.log"
        with scenario.create_scheduler(py_path, "world") as scheduler:
            scheduler.poll(2)
        status = self.java("journal-status", manifest, py_path, "world").decode()
        self.assertIn(f"RUN_ID\t{scenario.journal_run_id}\n", status)
        self.assertIn("\ttrue\n", status)
        java_path = self.path / "java.log"
        self.java("journal-create", manifest, java_path, "world")
        self.java("journal-poll", manifest, java_path, "world", 2)
        self.assertEqual(py_path.read_bytes(), java_path.read_bytes())
        with scenario.open_scheduler(java_path, "world") as scheduler:
            self.assertTrue(scheduler.pending.recovery_required)
            scheduler.reconcile(scheduler.pending.transition.transition_id, "NOT_APPLIED", "synthetic-no-effect")
        self.assertIn("NEXT\t1\n", self.java("journal-status", manifest, java_path, "world").decode())

    def test_empty_control_scope_seed_mode_and_trial_mismatches_rejected_both(self):
        scenario = Scenario(small_config(), 0, "no_event", "trial")
        manifest = self.path / "valid.manifest"; manifest.write_bytes(scenario.manifest)
        journal = self.path / "empty.log"
        self.java("journal-create", manifest, journal, "world")
        with scenario.open_scheduler(journal, "world") as scheduler:
            scheduler.poll(0)
        before = journal.read_bytes()
        for index, other in enumerate([Scenario(small_config(x=1), 0, "no_event", "trial"),
                                       Scenario(small_config(), 1, "no_event", "trial"),
                                       Scenario(small_config(), 0, "no_event", "other"),
                                       Scenario(small_config(), 0, "sham", "trial")]):
            file = self.path / f"other-{index}.manifest"; file.write_bytes(other.manifest)
            with self.assertRaises((ValueError, OSError)):
                other.open_scheduler(journal, "world")
            self.java("journal-status", file, journal, "world", success=False)
        self.assertEqual(before, journal.read_bytes())

    def test_manifest_tampering_rejected_in_both_languages(self):
        scene = Scenario(basic(), 7, "treatment", "trial")
        variants = [scene.manifest[:-1], scene.manifest + b"EXTRA\n", scene.manifest.replace(b"manifest:v1", b"manifest:v2"),
                    scene.manifest.replace(b"SEED\t7", b"SEED\t8"), scene.manifest.replace(b"MODE\ttreatment", b"MODE\tsham"),
                    scene.manifest.replace(b"TRIAL\ttrial", b"TRIAL\tother"), scene.manifest.replace(b"TARGET\t10", b"TARGET\t99"),
                    scene.manifest.replace(b"\n", b"\r\n"), scene.manifest.replace(b"GENERATOR\tsha256-counter-rejection-v1", b"GENERATOR\tunknown")]
        for index, data in enumerate(variants):
            with self.subTest(index=index):
                file = self.path / f"bad-{index}.manifest"; file.write_bytes(data)
                with self.assertRaises(ValueError):
                    Scenario.from_manifest(data)
                self.java("roundtrip", file, success=False)


if __name__ == "__main__":
    unittest.main()
