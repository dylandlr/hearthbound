package dev.hearthbound.experiment;

import java.io.IOException;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

/** Seeded, scoped experiment plans. No world mutation, actor feed, rewards, or physical sham proof. */
public final class EventScenarios {
    public static final int MAX_SCOPES = 64, MAX_RULES = 64, MAX_TARGETS = 256, MAX_AXIS_SIZE = 256;
    public static final int MAX_SELECTED_TARGETS = 65536, MAX_CONFIG_BYTES = 1024 * 1024;
    public static final int MAX_MANIFEST_BYTES = 16 * 1024 * 1024, PPM = 1_000_000;
    public static final String GENERATOR = "sha256-counter-rejection-v1";
    private static final Set<String> BLOCK_KINDS = Set.of("crop_failure", "mill_failure", "resource_depletion");
    private static final Pattern TOKEN = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{0,63}");
    private static final Pattern DIMENSION = Pattern.compile("[a-z0-9_.-]+:[a-z0-9_./-]+");
    private static final Pattern NAT = Pattern.compile("0|[1-9][0-9]*");
    private static final Pattern SIGNED = Pattern.compile("0|-?[1-9][0-9]*");
    private static final BigInteger TWO_256 = BigInteger.ONE.shiftLeft(256), TWO_63 = BigInteger.ONE.shiftLeft(63);
    private EventScenarios() {}

    public enum Mode {
        TREATMENT("treatment"), SHAM("sham"), NO_EVENT("no_event");
        private final String wire;
        Mode(String wire) { this.wire = wire; }
        public String wire() { return wire; }
        public static Mode fromWire(String text) {
            for (Mode mode : values()) if (mode.wire.equals(text)) return mode;
            throw new IllegalArgumentException("invalid scenario mode");
        }
    }
    public record Position(int x, int y, int z) implements Comparable<Position> {
        public String wire() { return x + "\t" + y + "\t" + z; }
        @Override public int compareTo(Position other) {
            int result = Integer.compare(x, other.x);
            if (result == 0) result = Integer.compare(y, other.y);
            return result == 0 ? Integer.compare(z, other.z) : result;
        }
    }
    public record Scope(String scopeId, String dimension, Position minimum, Position maximum, List<Position> targets) {
        public Scope {
            token(scopeId);
            if (dimension == null || dimension.length() > 128 || !DIMENSION.matcher(dimension).matches()
                    || minimum == null || maximum == null) throw new IllegalArgumentException("invalid scope identity or region");
            axis(minimum.x(), maximum.x()); axis(minimum.y(), maximum.y()); axis(minimum.z(), maximum.z());
            if (targets == null || targets.isEmpty() || targets.size() > MAX_TARGETS)
                throw new IllegalArgumentException("invalid target count");
            var sorted = new ArrayList<Position>(); var seen = new HashSet<Position>();
            for (Position position : targets) {
                if (position == null || !seen.add(position) || position.x() < minimum.x() || position.x() > maximum.x()
                        || position.y() < minimum.y() || position.y() > maximum.y()
                        || position.z() < minimum.z() || position.z() > maximum.z())
                    throw new IllegalArgumentException("duplicate target or target outside permitted region");
                sorted.add(position);
            }
            sorted.sort(Comparator.naturalOrder()); targets = List.copyOf(sorted);
        }
        private void append(StringBuilder out) {
            out.append("SCOPE\t").append(scopeId).append('\t').append(dimension).append('\t').append(minimum.wire())
                .append('\t').append(maximum.wire()).append('\t').append(targets.size()).append('\n');
            for (Position position : targets) out.append("BLOCK\t").append(position.wire()).append('\n');
        }
        public String digest() {
            var out = new StringBuilder("hearthbound:scenario-scope:v1\n"); append(out); return hash(out.toString());
        }
    }
    public record Rule(String ruleId, String kind, int count, long onsetMin, long onsetMax,
                       long durationMin, long durationMax, int severityMinPpm, int severityMaxPpm,
                       int targetsPerEvent, List<String> scopeIds) {
        public Rule {
            token(ruleId);
            if (kind == null || !BLOCK_KINDS.contains(kind)) throw new IllegalArgumentException("unsupported block-scoped kind");
            range(count, 1, EventScheduler.MAX_EVENTS); range(onsetMin, 0, Long.MAX_VALUE);
            range(onsetMax, onsetMin, Long.MAX_VALUE); range(durationMin, 1, Long.MAX_VALUE);
            range(durationMax, durationMin, Long.MAX_VALUE);
            if (onsetMax > Long.MAX_VALUE - durationMax) throw new IllegalArgumentException("worst-case end tick overflow");
            range(severityMinPpm, 0, PPM); range(severityMaxPpm, severityMinPpm, PPM); range(targetsPerEvent, 1, MAX_TARGETS);
            if (scopeIds == null || scopeIds.isEmpty() || scopeIds.size() > MAX_SCOPES)
                throw new IllegalArgumentException("invalid scope choice count");
            var sorted = new ArrayList<String>(); var seen = new HashSet<String>();
            for (String identity : scopeIds) {
                token(identity);
                if (!seen.add(identity)) throw new IllegalArgumentException("duplicate scope choice");
                sorted.add(identity);
            }
            sorted.sort(Comparator.naturalOrder()); scopeIds = List.copyOf(sorted);
        }
        private void append(StringBuilder out) {
            out.append("RULE\t").append(ruleId).append('\t').append(kind).append('\t').append(count).append('\t')
                .append(onsetMin).append('\t').append(onsetMax).append('\t').append(durationMin).append('\t')
                .append(durationMax).append('\t').append(severityMinPpm).append('\t').append(severityMaxPpm).append('\t')
                .append(targetsPerEvent).append('\t').append(scopeIds.size()).append('\n');
            for (String identity : scopeIds) out.append("USE_SCOPE\t").append(identity).append('\n');
        }
    }

    public static final class Config {
        private final List<Scope> scopes;
        private final List<Rule> rules;
        private final byte[] canonical;
        private final String digest;
        public Config(List<Scope> scopes, List<Rule> rules) {
            if (scopes == null || rules == null || scopes.size() > MAX_SCOPES || rules.size() > MAX_RULES)
                throw new IllegalArgumentException("excessive scope or rule count");
            var sortedScopes = new ArrayList<Scope>(); var byId = new HashMap<String, Scope>();
            for (Scope scope : scopes) {
                if (scope == null || byId.putIfAbsent(scope.scopeId(), scope) != null)
                    throw new IllegalArgumentException("duplicate or null scope");
                sortedScopes.add(scope);
            }
            var sortedRules = new ArrayList<Rule>(); var identities = new HashSet<String>();
            long events = 0, selections = 0;
            for (Rule rule : rules) {
                if (rule == null || !identities.add(rule.ruleId())) throw new IllegalArgumentException("duplicate or null rule");
                events += rule.count(); selections += (long) rule.count() * rule.targetsPerEvent();
                for (String identity : rule.scopeIds()) {
                    Scope scope = byId.get(identity);
                    if (scope == null || scope.targets().size() < rule.targetsPerEvent())
                        throw new IllegalArgumentException("unknown scope or insufficient targets");
                }
                sortedRules.add(rule);
            }
            if (events > EventScheduler.MAX_EVENTS || selections > MAX_SELECTED_TARGETS)
                throw new IllegalArgumentException("planned event or target selection capacity exceeded");
            sortedScopes.sort(Comparator.comparing(Scope::scopeId)); sortedRules.sort(Comparator.comparing(Rule::ruleId));
            this.scopes = List.copyOf(sortedScopes); this.rules = List.copyOf(sortedRules);
            var out = new StringBuilder("hearthbound:scenario-config:v1\nSCOPES\t").append(scopes.size()).append('\n');
            for (Scope scope : this.scopes) scope.append(out);
            out.append("RULES\t").append(rules.size()).append('\n');
            for (Rule rule : this.rules) rule.append(out);
            canonical = out.toString().getBytes(StandardCharsets.US_ASCII);
            if (canonical.length > MAX_CONFIG_BYTES) throw new IllegalArgumentException("configuration byte capacity exceeded");
            digest = hash(canonical);
        }
        public List<Scope> scopes() { return scopes; }
        public List<Rule> rules() { return rules; }
        public byte[] canonical() { return canonical.clone(); }
        public String digest() { return digest; }
        public static Config fromBytes(byte[] supplied) {
            byte[] data = document(supplied, MAX_CONFIG_BYTES); Reader reader = new Reader(data);
            if (!reader.raw().equals("hearthbound:scenario-config:v1")) throw new IllegalArgumentException("unsupported config version");
            int count = count(reader.fields("SCOPES", 1)[0], 0, MAX_SCOPES);
            var scopes = new ArrayList<Scope>();
            for (int index = 0; index < count; index++) {
                String[] f = reader.fields("SCOPE", 9);
                int targetCount = count(f[8], 1, MAX_TARGETS);
                Position low = new Position(coordinate(f[2]), coordinate(f[3]), coordinate(f[4]));
                Position high = new Position(coordinate(f[5]), coordinate(f[6]), coordinate(f[7]));
                var targets = new ArrayList<Position>();
                for (int target = 0; target < targetCount; target++) {
                    String[] p = reader.fields("BLOCK", 3);
                    targets.add(new Position(coordinate(p[0]), coordinate(p[1]), coordinate(p[2])));
                }
                scopes.add(new Scope(f[0], f[1], low, high, targets));
            }
            count = count(reader.fields("RULES", 1)[0], 0, MAX_RULES); var rules = new ArrayList<Rule>();
            for (int index = 0; index < count; index++) {
                String[] f = reader.fields("RULE", 11); int scopeCount = count(f[10], 1, MAX_SCOPES);
                var identities = new ArrayList<String>();
                for (int scope = 0; scope < scopeCount; scope++) identities.add(reader.fields("USE_SCOPE", 1)[0]);
                rules.add(new Rule(f[0], f[1], count(f[2], 1, EventScheduler.MAX_EVENTS), number(f[3]), number(f[4]),
                    number(f[5]), number(f[6]), count(f[7], 0, PPM), count(f[8], 0, PPM), count(f[9], 1, MAX_TARGETS), identities));
            }
            if (!reader.finished()) throw new IllegalArgumentException("trailing configuration records");
            Config config = new Config(scopes, rules);
            if (!Arrays.equals(config.canonical, data)) throw new IllegalArgumentException("noncanonical configuration");
            return config;
        }
    }

    public record Choice(String ruleId, int ordinal, String pairId, String kind, Scope scope, List<Position> targets,
                         String targetDigest, long onset, long duration, int intendedPpm, Integer effectivePpm,
                         EventScheduler.Event event) {
        public Choice { targets = List.copyOf(targets); }
    }
    public static final class Scenario {
        private final Config config;
        private final long seed;
        private final Mode mode;
        private final String trialId, samplingKey, manifestDigest, journalRunId;
        private final List<Choice> choices;
        private final EventScheduler.Schedule schedule;
        private final byte[] manifest;
        private final Map<String, Choice> byEvent;
        private Scenario(Config config, long seed, Mode mode, String trialId) {
            if (config == null || mode == null || seed < 0) throw new IllegalArgumentException("invalid scenario inputs");
            token(trialId); this.config = config; this.seed = seed; this.mode = mode; this.trialId = trialId;
            samplingKey = hash("hearthbound:scenario-sampling:v1\n" + config.digest + "\n" + seed + "\n");
            String context = hash("hearthbound:scenario-context:v1\n" + config.digest + "\n" + seed + "\n" + mode.wire() + "\n" + trialId + "\n");
            var scopes = new HashMap<String, Scope>(); var scopeHashes = new HashMap<String, String>();
            for (Scope scope : config.scopes) { scopes.put(scope.scopeId(), scope); scopeHashes.put(scope.scopeId(), scope.digest()); }
            var planned = new ArrayList<Choice>(); var emitted = new ArrayList<EventScheduler.Event>(); var lookup = new HashMap<String, Choice>();
            Sampler sampler = new Sampler(samplingKey);
            for (Rule rule : config.rules) {
                for (int ordinal = 0; ordinal < rule.count(); ordinal++) {
                    int scopeIndex = (int) sampler.bounded(rule.ruleId(), ordinal, "scope", BigInteger.valueOf(rule.scopeIds().size()));
                    Scope scope = scopes.get(rule.scopeIds().get(scopeIndex)); String scopeHash = scopeHashes.get(scope.scopeId());
                    long onset = sampler.inclusive(rule.ruleId(), ordinal, "onset", rule.onsetMin(), rule.onsetMax());
                    long duration = sampler.inclusive(rule.ruleId(), ordinal, "duration", rule.durationMin(), rule.durationMax());
                    int intended = (int) sampler.inclusive(rule.ruleId(), ordinal, "severity", rule.severityMinPpm(), rule.severityMaxPpm());
                    var available = new ArrayList<>(scope.targets());
                    for (int target = 0; target < rule.targetsPerEvent(); target++) {
                        int selected = target + (int) sampler.bounded(rule.ruleId(), ordinal, "target-" + target, BigInteger.valueOf(available.size() - target));
                        Position swap = available.get(target); available.set(target, available.get(selected)); available.set(selected, swap);
                    }
                    var targets = new ArrayList<>(available.subList(0, rule.targetsPerEvent())); targets.sort(Comparator.naturalOrder());
                    var targetWire = new StringBuilder("hearthbound:scenario-targets:v1\n").append(scopeHash).append('\n');
                    for (Position target : targets) targetWire.append(target.wire()).append('\n');
                    String targetDigest = hash(targetWire.toString());
                    String pairId = hash("hearthbound:scenario-pair:v1\n" + samplingKey + "\n" + rule.ruleId() + "\n" + ordinal + "\n");
                    Integer effective = mode == Mode.TREATMENT ? Integer.valueOf(intended) : mode == Mode.SHAM ? Integer.valueOf(0) : null;
                    EventScheduler.Event event = null;
                    if (mode != Mode.NO_EVENT) {
                        String identity = hash("hearthbound:scenario-event:v1\n" + context + "\n" + rule.ruleId() + "\n" + ordinal + "\n"
                            + scopeHash + "\n" + targetDigest + "\n" + onset + "\n" + duration + "\n" + intended + "\n");
                        event = new EventScheduler.Event(identity, rule.kind(), onset, duration, effective.doubleValue() / PPM);
                        emitted.add(event);
                    }
                    Choice choice = new Choice(rule.ruleId(), ordinal, pairId, rule.kind(), scope, targets, targetDigest, onset, duration, intended, effective, event);
                    planned.add(choice); if (event != null) lookup.put(event.eventId(), choice);
                }
            }
            choices = List.copyOf(planned); byEvent = Map.copyOf(lookup); schedule = new EventScheduler.Schedule(emitted);
            var out = new StringBuilder("hearthbound:scenario-manifest:v1\nGENERATOR\t").append(GENERATOR)
                .append("\nSEED\t").append(seed).append("\nMODE\t").append(mode.wire()).append("\nTRIAL\t").append(trialId)
                .append("\nCONFIG_BYTES\t").append(config.canonical.length).append('\n')
                .append(new String(config.canonical, StandardCharsets.US_ASCII)).append("CONFIG_SHA256\t").append(config.digest)
                .append("\nCHOICES\t").append(choices.size()).append('\n');
            for (Choice choice : choices) {
                out.append("CHOICE\t").append(choice.ruleId()).append('\t').append(choice.ordinal()).append('\t').append(choice.pairId())
                    .append('\t').append(choice.kind()).append('\t').append(choice.scope().scopeId()).append('\t').append(scopeHashes.get(choice.scope().scopeId()))
                    .append('\t').append(choice.targetDigest()).append('\t').append(choice.onset()).append('\t').append(choice.duration())
                    .append('\t').append(choice.intendedPpm()).append('\t').append(choice.effectivePpm() == null ? "-" : choice.effectivePpm())
                    .append('\t').append(choice.event() == null ? "-" : choice.event().eventId()).append('\t').append(choice.targets().size()).append('\n');
                for (Position target : choice.targets()) out.append("TARGET\t").append(target.wire()).append('\n');
            }
            out.append("SCHEDULE_SHA256\t").append(schedule.digest()).append("\nEVENT_COUNT\t").append(schedule.events().size()).append('\n');
            manifest = out.toString().getBytes(StandardCharsets.US_ASCII);
            if (manifest.length > MAX_MANIFEST_BYTES) throw new IllegalArgumentException("manifest byte capacity exceeded");
            manifestDigest = hash(manifest);
            journalRunId = hash("hearthbound:scenario-run:v1\n" + manifestDigest + "\n" + trialId + "\n");
        }
        public Config config() { return config; }
        public long seed() { return seed; }
        public Mode mode() { return mode; }
        public String trialId() { return trialId; }
        public String samplingKey() { return samplingKey; }
        public List<Choice> choices() { return choices; }
        public EventScheduler.Schedule schedule() { return schedule; }
        public byte[] manifest() { return manifest.clone(); }
        public String manifestDigest() { return manifestDigest; }
        public String journalRunId() { return journalRunId; }
        public Choice eventChoice(String identity) {
            Choice choice = identity == null ? null : byEvent.get(identity);
            if (choice == null) throw new IllegalArgumentException("unknown or foreign scenario event");
            return choice;
        }
        public EventScheduler createScheduler(Path path, String world) throws IOException {
            return EventScheduler.create(path, schedule.events(), world, journalRunId);
        }
        public EventScheduler openScheduler(Path path, String world) throws IOException {
            return EventScheduler.open(path, schedule.events(), world, journalRunId);
        }
    }
    public static Scenario generate(Config config, long seed, Mode mode, String trialId) { return new Scenario(config, seed, mode, trialId); }
    public static Scenario fromManifest(byte[] supplied) {
        byte[] data = document(supplied, MAX_MANIFEST_BYTES);
        String[] parts = new String(data, StandardCharsets.US_ASCII).split("\n", 7);
        if (parts.length != 7 || !parts[0].equals("hearthbound:scenario-manifest:v1") || !parts[1].equals("GENERATOR\t" + GENERATOR))
            throw new IllegalArgumentException("unsupported manifest or generator version");
        String[] tags = {"SEED", "MODE", "TRIAL", "CONFIG_BYTES"}; String[] values = new String[4];
        for (int index = 0; index < 4; index++) {
            String[] f = parts[index + 2].split("\t", -1);
            if (f.length != 2 || !f[0].equals(tags[index])) throw new IllegalArgumentException("invalid manifest header");
            values[index] = f[1];
        }
        int length = count(values[3], 1, MAX_CONFIG_BYTES);
        if (parts[6].length() < length) throw new IllegalArgumentException("truncated embedded configuration");
        Config config = Config.fromBytes(parts[6].substring(0, length).getBytes(StandardCharsets.US_ASCII));
        Scenario scenario = generate(config, number(values[0]), Mode.fromWire(values[1]), values[2]);
        if (!Arrays.equals(scenario.manifest, data)) throw new IllegalArgumentException("manifest differs from complete regenerated scenario");
        return scenario;
    }

    @FunctionalInterface interface Digest { byte[] apply(byte[] message); }
    static final class Sampler {
        private final String key; private final Digest digest;
        Sampler(String key) { this(key, EventScenarios::hashBytes); }
        Sampler(String key, Digest digest) { this.key = Objects.requireNonNull(key); this.digest = Objects.requireNonNull(digest); }
        long bounded(String rule, int ordinal, String field, BigInteger bound) {
            if (bound == null || bound.signum() <= 0 || bound.compareTo(TWO_63) > 0) throw new IllegalArgumentException("invalid draw bound");
            BigInteger limit = TWO_256.subtract(TWO_256.mod(bound));
            for (int attempt = 0; attempt < 1024; attempt++) {
                byte[] message = ("hearthbound:scenario-draw:v1\n" + key + "\n" + rule + "\n" + ordinal + "\n" + field + "\n" + attempt + "\n")
                    .getBytes(StandardCharsets.US_ASCII);
                byte[] raw = digest.apply(message);
                if (raw == null || raw.length != 32) throw new IllegalArgumentException("invalid SHA-256 draw");
                BigInteger value = new BigInteger(1, raw);
                if (value.compareTo(limit) < 0) return value.mod(bound).longValueExact();
            }
            throw new IllegalArgumentException("deterministic draw rejection budget exhausted");
        }
        long inclusive(String rule, int ordinal, String field, long low, long high) {
            range(low, 0, Long.MAX_VALUE); range(high, low, Long.MAX_VALUE);
            BigInteger bound = BigInteger.valueOf(high).subtract(BigInteger.valueOf(low)).add(BigInteger.ONE);
            return Math.addExact(low, bounded(rule, ordinal, field, bound));
        }
    }
    private static final class Reader {
        private final String[] lines; private int index;
        Reader(byte[] data) { String[] all = new String(data, StandardCharsets.US_ASCII).split("\n", -1); lines = Arrays.copyOf(all, all.length - 1); }
        String raw() { if (index == lines.length) throw new IllegalArgumentException("truncated configuration"); return lines[index++]; }
        String[] fields(String tag, int count) {
            String[] f = raw().split("\t", -1);
            if (f.length != count + 1 || !f[0].equals(tag)) throw new IllegalArgumentException("invalid configuration record");
            return Arrays.copyOfRange(f, 1, f.length);
        }
        boolean finished() { return index == lines.length; }
    }
    private static void axis(int low, int high) { range((long) high - low + 1, 1, MAX_AXIS_SIZE); }
    private static void token(String text) {
        if (text == null || !TOKEN.matcher(text).matches()) throw new IllegalArgumentException("invalid scenario identity");
    }
    private static void range(long value, long low, long high) {
        if (value < low || value > high) throw new IllegalArgumentException("value outside scenario bounds");
    }
    private static long number(String text) {
        if (!NAT.matcher(text).matches() || text.length() > 19) throw new IllegalArgumentException("noncanonical scenario integer");
        try { return Long.parseLong(text); } catch (NumberFormatException error) { throw new IllegalArgumentException("scenario integer overflow", error); }
    }
    private static int count(String text, int low, int high) { long value = number(text); range(value, low, high); return (int) value; }
    private static int coordinate(String text) {
        if (!SIGNED.matcher(text).matches() || text.length() > 11) throw new IllegalArgumentException("noncanonical coordinate");
        try { return Integer.parseInt(text); } catch (NumberFormatException error) { throw new IllegalArgumentException("coordinate overflow", error); }
    }
    private static byte[] document(byte[] data, int limit) {
        if (data == null || data.length == 0 || data.length > limit) throw new IllegalArgumentException("invalid bounded document");
        byte[] copy = data.clone();
        if (copy[copy.length - 1] != '\n') throw new IllegalArgumentException("missing final newline");
        for (byte raw : copy) {
            int value = Byte.toUnsignedInt(raw);
            if (value != '\n' && value != '\t' && (value < 32 || value > 126)) throw new IllegalArgumentException("noncanonical document byte");
        }
        return copy;
    }
    private static String hash(String value) { return hash(value.getBytes(StandardCharsets.US_ASCII)); }
    private static String hash(byte[] value) { return HexFormat.of().formatHex(hashBytes(value)); }
    private static byte[] hashBytes(byte[] value) {
        try { return MessageDigest.getInstance("SHA-256").digest(value); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
