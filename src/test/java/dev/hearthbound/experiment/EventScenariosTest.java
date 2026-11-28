package dev.hearthbound.experiment;

import java.io.IOException;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import dev.hearthbound.experiment.EventScenarios.*;

/** Fixed independent fixtures and scoped scenario contracts; no physical effect is executed. */
public final class EventScenariosTest {
    @FunctionalInterface interface Checked { void run() throws Exception; }
    private static int passed;
    private static final Path FIXTURES = Path.of("tests/fixtures/event_scenarios");
    private static void check(boolean value) { if (!value) throw new AssertionError("scenario contract failed"); }
    private static void reject(Checked code) throws Exception {
        try { code.run(); } catch (IllegalArgumentException | IllegalStateException | IOException expected) { return; }
        throw new AssertionError("invalid scenario accepted");
    }
    private static void test(String name, Checked code) throws Exception { code.run(); passed++; System.out.println("PASS " + name); }
    private static Config basic() throws Exception { return Config.fromBytes(Files.readAllBytes(FIXTURES.resolve("basic.config"))); }
    private static Config small(int x, long low, long high, long durationLow, long durationHigh, int count) {
        Position position = new Position(x, 64, 0);
        return new Config(List.of(new Scope("plot", "minecraft:overworld", position, position, List.of(position))),
            List.of(new Rule("crop", "crop_failure", count, low, high, durationLow, durationHigh, 500000, 500000, 1, List.of("plot"))));
    }
    private static Config small() { return small(0, 2, 2, 1, 1, 1); }
    private static List<String> latent(Scenario scenario) {
        return scenario.choices().stream().map(c -> c.ruleId() + ":" + c.ordinal() + ":" + c.pairId() + ":" + c.kind() + ":"
            + c.scope() + ":" + c.targets() + ":" + c.targetDigest() + ":" + c.onset() + ":" + c.duration() + ":" + c.intendedPpm()).toList();
    }
    public static void main(String[] args) throws Exception {
        test("nine frozen manifest oracles including maximum seed and all modes", () -> {
            Config config = basic();
            check(config.digest().equals("00579fa97894a6759e7115109213e82bf0b4f3065105a4a0679337b3b53b9a78"));
            for (String line : Files.readAllLines(FIXTURES.resolve("golden-index.tsv"), StandardCharsets.US_ASCII)) {
                String[] f = line.split("\t");
                Scenario scene = EventScenarios.generate(config, Long.parseLong(f[0]), Mode.fromWire(f[1]), f[2]);
                byte[] oracle = Files.readAllBytes(FIXTURES.resolve(f[3]));
                check(Arrays.equals(oracle, scene.manifest())); check(scene.manifestDigest().equals(f[4]));
                check(scene.schedule().digest().equals(f[5])); check(scene.journalRunId().equals(f[6]));
                check(Arrays.equals(oracle, EventScenarios.fromManifest(oracle).manifest()));
            }
            Scenario zero = EventScenarios.generate(config, 0, Mode.TREATMENT, "trial-treatment");
            check(zero.choices().get(0).onset() == 12 && zero.choices().get(0).duration() == 2 && zero.choices().get(0).intendedPpm() == 165598);
            check(zero.choices().get(0).targets().equals(List.of(new Position(0, 64, 0), new Position(1, 64, 1))));
        });
        test("paired treatment, sham and no-event retain identical latent choices", () -> {
            Scenario treatment = EventScenarios.generate(basic(), 7, Mode.TREATMENT, "arm-treatment");
            Scenario sham = EventScenarios.generate(basic(), 7, Mode.SHAM, "arm-sham");
            Scenario none = EventScenarios.generate(basic(), 7, Mode.NO_EVENT, "arm-none");
            check(latent(treatment).equals(latent(sham)) && latent(sham).equals(latent(none)));
            check(sham.schedule().events().size() == 3 && none.schedule().events().isEmpty());
            check(sham.choices().stream().allMatch(c -> c.intendedPpm() > 0 && c.effectivePpm() == 0 && c.event().severity() == 0));
            check(none.choices().stream().allMatch(c -> c.effectivePpm() == null && c.event() == null));
            check(!treatment.journalRunId().equals(sham.journalRunId()) && !sham.journalRunId().equals(none.journalRunId()));
            check(treatment.schedule().events().stream().noneMatch(e -> sham.schedule().events().contains(e)));
        });
        test("repeatability, seed variation and trial provenance", () -> {
            Scenario a = EventScenarios.generate(basic(), 0, Mode.TREATMENT, "trial");
            Scenario again = EventScenarios.generate(basic(), 0, Mode.TREATMENT, "trial");
            Scenario otherSeed = EventScenarios.generate(basic(), 7, Mode.TREATMENT, "trial");
            Scenario otherTrial = EventScenarios.generate(basic(), 0, Mode.TREATMENT, "other");
            check(Arrays.equals(a.manifest(), again.manifest())); check(!latent(a).equals(latent(otherSeed)));
            check(latent(a).equals(latent(otherTrial)) && !a.journalRunId().equals(otherTrial.journalRunId()));
            check(new String(otherTrial.manifest(), StandardCharsets.US_ASCII).contains("TRIAL\tother\n"));
        });
        test("canonical reordering and immutable deep views", () -> {
            Config original = basic(); var scopes = new ArrayList<Scope>(); var rules = new ArrayList<Rule>();
            for (Scope scope : original.scopes()) {
                var targets = new ArrayList<>(scope.targets()); Collections.reverse(targets);
                scopes.add(new Scope(scope.scopeId(), scope.dimension(), scope.minimum(), scope.maximum(), targets)); targets.clear();
            }
            for (Rule r : original.rules()) {
                var ids = new ArrayList<>(r.scopeIds()); Collections.reverse(ids);
                rules.add(new Rule(r.ruleId(), r.kind(), r.count(), r.onsetMin(), r.onsetMax(), r.durationMin(), r.durationMax(),
                    r.severityMinPpm(), r.severityMaxPpm(), r.targetsPerEvent(), ids)); ids.clear();
            }
            Collections.reverse(scopes); Collections.reverse(rules); Config reordered = new Config(scopes, rules); scopes.clear(); rules.clear();
            check(Arrays.equals(original.canonical(), reordered.canonical()));
            Scenario scene = EventScenarios.generate(reordered, 7, Mode.TREATMENT, "trial");
            check(Arrays.equals(scene.manifest(), EventScenarios.generate(original, 7, Mode.TREATMENT, "trial").manifest()));
            byte[] old = scene.manifest(); byte[] copy = scene.manifest(); copy[0] = '?'; check(Arrays.equals(old, scene.manifest()));
            byte[] cfgCopy = reordered.canonical(); cfgCopy[0] = '?'; check(Arrays.equals(original.canonical(), reordered.canonical()));
            try { scene.choices().get(0).targets().clear(); throw new AssertionError(); } catch (UnsupportedOperationException expected) {}
            try { reordered.scopes().clear(); throw new AssertionError(); } catch (UnsupportedOperationException expected) {}
        });
        test("invalid scope identities, coordinates and permitted regions", () -> {
            Position p = new Position(0, 64, 0);
            reject(() -> new Scope("bad:id", "minecraft:overworld", p, p, List.of(p)));
            reject(() -> new Scope("s", "overworld", p, p, List.of(p)));
            reject(() -> new Scope("s", "Minecraft:overworld", p, p, List.of(p)));
            reject(() -> new Scope("s", "minecraft:overworld", p, new Position(256, 64, 0), List.of(p)));
            reject(() -> new Scope("s", "minecraft:overworld", p, new Position(-1, 64, 0), List.of(p)));
            reject(() -> new Scope("s", "minecraft:overworld", p, p, List.of()));
            reject(() -> new Scope("s", "minecraft:overworld", p, p, List.of(p, p)));
            reject(() -> new Scope("s", "minecraft:overworld", p, p, List.of(new Position(1, 64, 0))));
            Position edge = new Position(Integer.MIN_VALUE, Integer.MAX_VALUE, 0);
            Config edgeConfig = new Config(List.of(new Scope("edge", "minecraft:overworld", edge, edge, List.of(edge))), List.of());
            check(Config.fromBytes(edgeConfig.canonical()).scopes().get(0).minimum().equals(edge));
            reject(() -> Config.fromBytes(new String(edgeConfig.canonical(), StandardCharsets.US_ASCII).replace("-2147483648", "-2147483649").getBytes(StandardCharsets.US_ASCII)));
        });
        test("range, seed, event-kind and reference rejection", () -> {
            for (String kind : List.of("specialist_loss", "communication_failure", "demand_change", "unknown"))
                reject(() -> new Rule("r", kind, 1, 0, 0, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 0, 0, 0, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 4097, 0, 0, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, -1, 0, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 0, Long.MAX_VALUE, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 1, 1, 1, Long.MAX_VALUE, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 0, 0, 0, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 0, 0, 1, 1, -1, 1, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 0, 0, 1, 1, 0, 1000001, 1, List.of("plot")));
            reject(() -> new Rule("r", "crop_failure", 1, 0, 0, 1, 1, 0, 1, 1, List.of("plot", "plot")));
            reject(() -> new Config(small().scopes(), List.of(new Rule("r", "crop_failure", 1, 0, 0, 1, 1, 0, 1, 1, List.of("unknown")))));
            reject(() -> new Config(small().scopes(), List.of(new Rule("r", "crop_failure", 1, 0, 0, 1, 1, 0, 1, 2, List.of("plot")))));
            reject(() -> EventScenarios.generate(small(), -1, Mode.TREATMENT, "trial"));
            reject(() -> EventScenarios.generate(small(), 0, null, "trial"));
            reject(() -> EventScenarios.generate(small(), 0, Mode.SHAM, "bad\ntrial"));
        });
        test("total count limits and maximum valid target selection", () -> {
            Config config = small(); Rule rule = config.rules().get(0);
            reject(() -> new Config(List.of(config.scopes().get(0), config.scopes().get(0)), List.of(rule)));
            reject(() -> new Config(config.scopes(), List.of(rule, rule)));
            var scopes = new ArrayList<Scope>();
            for (int i = 0; i < 65; i++) scopes.add(new Scope("s" + i, "minecraft:overworld", new Position(0, 0, 0), new Position(0, 0, 0), List.of(new Position(0, 0, 0))));
            reject(() -> new Config(scopes, List.of()));
            var rules = new ArrayList<Rule>();
            for (int i = 0; i < 65; i++) rules.add(new Rule("r" + i, "crop_failure", 1, 0, 0, 1, 1, 0, 1, 1, List.of("plot")));
            reject(() -> new Config(config.scopes(), rules));
            var points = new ArrayList<Position>(); for (int i = 0; i < 256; i++) points.add(new Position(i, 64, 0));
            Scope wide = new Scope("plot", "minecraft:overworld", points.get(0), points.get(255), points);
            reject(() -> new Config(List.of(wide), List.of(new Rule("r", "crop_failure", 4096, 0, 0, 1, 1, 0, 1, 17, List.of("plot")))));
            Config fullTargets = new Config(List.of(wide), List.of(new Rule("r", "crop_failure", 1, 0, 0, 1, 1, 0, 1, 256, List.of("plot"))));
            check(EventScenarios.generate(fullTargets, 7, Mode.SHAM, "all").choices().get(0).targets().equals(points));
            Scenario capacity = EventScenarios.generate(small(0, 0, 0, 1, 1, 4096), 0, Mode.TREATMENT, "capacity");
            check(capacity.schedule().events().size() == 4096);
            check(capacity.schedule().events().stream().map(EventScheduler.Event::eventId).distinct().count() == 4096);
        });
        test("full signed-long ranges and forced rejection sampling", () -> {
            for (Config config : List.of(small(0, 0, Long.MAX_VALUE - 1, 1, 1, 1), small(0, 0, 0, 1, Long.MAX_VALUE, 1))) {
                Choice c = EventScenarios.generate(config, Long.MAX_VALUE, Mode.TREATMENT, "edge").choices().get(0);
                check(c.onset() <= Long.MAX_VALUE - c.duration()); check(Math.max(c.onset(), c.duration()) > (1L << 32));
            }
            Choice edge = EventScenarios.generate(small(0, Long.MAX_VALUE - 1, Long.MAX_VALUE - 1, 1, 1, 1), Long.MAX_VALUE, Mode.SHAM, "edge").choices().get(0);
            check(edge.onset() + edge.duration() == Long.MAX_VALUE);
            byte[] ff = new byte[32]; Arrays.fill(ff, (byte) 255); var messages = new ArrayList<String>();
            var sampler = new EventScenarios.Sampler("0".repeat(64), data -> { messages.add(new String(data, StandardCharsets.US_ASCII)); return messages.size() == 1 ? ff : new byte[32]; });
            check(sampler.bounded("r", 0, "onset", BigInteger.valueOf(3)) == 0);
            check(messages.size() == 2 && messages.get(0).endsWith("\n0\n") && messages.get(1).endsWith("\n1\n"));
            check(new EventScenarios.Sampler("0".repeat(64), data -> ff).bounded("r", 0, "onset", BigInteger.ONE.shiftLeft(63)) == Long.MAX_VALUE);
            reject(() -> new EventScenarios.Sampler("k", data -> ff).bounded("r", 0, "x", BigInteger.valueOf(3)));
            reject(() -> new EventScenarios.Sampler("k", data -> new byte[1]).bounded("r", 0, "x", BigInteger.valueOf(3)));
            reject(() -> sampler.bounded("r", 0, "x", BigInteger.ZERO));
            reject(() -> sampler.bounded("r", 0, "x", BigInteger.ONE.shiftLeft(63).add(BigInteger.ONE)));
        });
        test("canonical document and complete manifest regeneration rejection", () -> {
            String config = new String(basic().canonical(), StandardCharsets.US_ASCII);
            for (String changed : List.of(config.substring(0, config.length() - 1), config + "EXTRA\n", config.replace("config:v1", "config:v2"),
                    config.replace("SCOPES\t2", "SCOPES\t02"), config.replace("\n", "\r\n"),
                    config.replace("BLOCK\t-2\t64\t0\nBLOCK\t-1\t64\t1", "BLOCK\t-1\t64\t1\nBLOCK\t-2\t64\t0")))
                reject(() -> Config.fromBytes(changed.getBytes(StandardCharsets.US_ASCII)));
            String manifest = new String(EventScenarios.generate(basic(), 7, Mode.TREATMENT, "trial").manifest(), StandardCharsets.US_ASCII);
            for (String changed : List.of(manifest.substring(0, manifest.length() - 1), manifest + "EXTRA\n", manifest.replace("manifest:v1", "manifest:v2"),
                    manifest.replace("SEED\t7", "SEED\t8"), manifest.replace("MODE\ttreatment", "MODE\tsham"),
                    manifest.replace("TRIAL\ttrial", "TRIAL\tother"), manifest.replace("TARGET\t10", "TARGET\t99")))
                reject(() -> EventScenarios.fromManifest(changed.getBytes(StandardCharsets.US_ASCII)));
            reject(() -> Config.fromBytes(new byte[EventScenarios.MAX_CONFIG_BYTES + 1]));
            reject(() -> EventScenarios.fromManifest(new byte[EventScenarios.MAX_MANIFEST_BYTES + 1]));
        });
        test("enforced wrapper binding including empty controls", () -> {
            Path directory = Files.createTempDirectory("hearthbound-scenario-bind-");
            for (Mode mode : List.of(Mode.TREATMENT, Mode.NO_EVENT)) {
                Scenario scene = EventScenarios.generate(small(), 0, mode, "trial"); Path journal = directory.resolve(mode.wire());
                try (var scheduler = scene.createScheduler(journal, "world")) { scheduler.poll(0); }
                byte[] before = Files.readAllBytes(journal);
                try (var scheduler = EventScenarios.fromManifest(scene.manifest()).openScheduler(journal, "world")) { check(scheduler.clock() == 0); }
                for (Scenario other : List.of(EventScenarios.generate(small(), 1, mode, "trial"), EventScenarios.generate(small(), 0, mode, "other"),
                        EventScenarios.generate(small(1, 2, 2, 1, 1, 1), 0, mode, "trial"), EventScenarios.generate(small(), 0, Mode.SHAM, "trial"))) {
                    check(!scene.manifestDigest().equals(other.manifestDigest()));
                    reject(() -> other.openScheduler(journal, "world"));
                }
                reject(() -> scene.openScheduler(journal, "foreign"));
                reject(() -> EventScheduler.open(journal, scene.schedule().events(), "world", scene.trialId()));
                check(Arrays.equals(before, Files.readAllBytes(journal)));
                if (mode == Mode.NO_EVENT) check(scene.schedule().digest().equals(EventScenarios.generate(small(1, 2, 2, 1, 1, 1), 0, mode, "trial").schedule().digest()));
                Files.delete(journal);
            }
            Files.delete(directory);
        });
        test("wrapper preserves pending recovery and exact scope lookup", () -> {
            Scenario scene = EventScenarios.generate(small(), 7, Mode.TREATMENT, "trial");
            Path directory = Files.createTempDirectory("hearthbound-scenario-recovery-"); Path journal = directory.resolve("journal"); String identity;
            try (var scheduler = scene.createScheduler(journal, "world")) {
                var intent = scheduler.poll(2); identity = intent.transition().transitionId();
                check(scene.eventChoice(intent.transition().eventId()).scope().equals(small().scopes().get(0)));
            }
            try (var scheduler = EventScenarios.fromManifest(scene.manifest()).openScheduler(journal, "world")) {
                check(scheduler.pending().recoveryRequired() && !scheduler.pending().executable());
                reject(() -> scheduler.acknowledge(identity, EventScheduler.Outcome.APPLIED, "false-witness", 2L));
                scheduler.reconcile(identity, EventScheduler.Outcome.NOT_APPLIED, "synthetic-no-effect", null);
                check(scheduler.nextIndex() == 1);
            }
            reject(() -> scene.eventChoice("unknown"));
            reject(() -> scene.eventChoice(EventScenarios.generate(small(1, 2, 2, 1, 1, 1), 7, Mode.TREATMENT, "trial").schedule().events().get(0).eventId()));
            Files.delete(journal); Files.delete(directory);
        });
        System.out.println("PASS " + passed + " Java seeded scenario contract groups; no native scope enforcement or physical sham validation");
    }
}
