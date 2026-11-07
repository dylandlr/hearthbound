package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Immutable 10-16-3 simulator-trained source-choice MLP, Java 17 inference.
 *
 * No world API, weights update, hidden inventory input or reward delivery.
 * A SHA-256 manifest created BEFORE Forge boots pins the exact model bytes.
 * Inputs are recipient-visible REPORT features only (not the hidden outcome).
 */
public final class ReportChoiceMlp {
    public static final String SCHEMA = "hearthbound.report-choice-mlp.v1";
    public static final String ORIGIN = "SIMULATED_SUPERVISED_OUTCOMES_ONLY";
    public static final String FEATURES =
        "present,wheat_norm,delivery_age_norm,observation_age_norm,revision_norm";
    public static final int INPUT = 10, HIDDEN = 16, OUTPUT = 3;
    public enum Action { SOURCE_A, SOURCE_B, ABSTAIN }
    private final double[] w1, b1, w2, b2;
    private final String sha256;

    private ReportChoiceMlp(double[] w1, double[] b1, double[] w2,
                            double[] b2, String sha) {
        this.w1 = w1;
        this.b1 = b1;
        this.w2 = w2;
        this.b2 = b2;
        this.sha256 = sha;
    }

    private static String value(String line, String key) {
        if (!line.startsWith(key + "=")) throw new IllegalArgumentException("Missing " + key);
        return line.substring(key.length() + 1);
    }

    private static double[] parse(String line, String key, int size) {
        String[] fields = value(line, key).split(",", -1);
        if (fields.length != size) throw new IllegalArgumentException("Wrong tensor shape: " + key);
        double[] numbers = new double[size];
        for (int i = 0; i < fields.length; i++) {
            numbers[i] = Double.parseDouble(fields[i]);
            if (!Double.isFinite(numbers[i]))
                throw new IllegalArgumentException("Non-finite model parameter");
        }
        return numbers;
    }

    public static ReportChoiceMlp load(Path model, Path shaManifest) throws Exception {
        Objects.requireNonNull(model);
        Objects.requireNonNull(shaManifest);
        byte[] bytes = Files.readAllBytes(model);
        if (bytes.length < 300 || bytes.length > 100_000)
            throw new IllegalArgumentException("Unbounded frozen model file");
        String expected = Files.readString(shaManifest, StandardCharsets.UTF_8).trim();
        if (!expected.matches("[a-f0-9]{64}"))
            throw new IllegalArgumentException("Invalid model checksum manifest");
        String actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if (!MessageDigest.isEqual(actual.getBytes(StandardCharsets.US_ASCII),
                                   expected.getBytes(StandardCharsets.US_ASCII)))
            throw new IllegalArgumentException("Frozen MLP SHA-256 mismatch");
        List<String> lines = Files.readAllLines(model, StandardCharsets.UTF_8);
        if (lines.size() != 11 || !SCHEMA.equals(lines.get(0))
                || !("origin=" + ORIGIN).equals(lines.get(1))
                || !("features=" + FEATURES).equals(lines.get(5))
                || !"dimensions=10,16,3".equals(lines.get(6))
                || Integer.parseInt(value(lines.get(3), "training_samples")) < 100
                || Integer.parseInt(value(lines.get(2), "training_seed")) < 0
                || Integer.parseInt(value(lines.get(4), "heldout_seed")) < 0)
            throw new IllegalArgumentException("Invalid frozen model provenance/schema");
        return new ReportChoiceMlp(
            parse(lines.get(7), "w1", INPUT * HIDDEN),
            parse(lines.get(8), "b1", HIDDEN),
            parse(lines.get(9), "w2", HIDDEN * OUTPUT),
            parse(lines.get(10), "b2", OUTPUT),
            actual);
    }

    public String sha256() { return sha256; }

    public double[] scores(double[] input) {
        if (input == null || input.length != INPUT)
            throw new IllegalArgumentException("Invalid report observation width");
        for (double v : input) {
            if (!Double.isFinite(v) || v < 0.0 || v > 1.0)
                throw new IllegalArgumentException("Invalid normalized report feature");
        }
        double[] hidden = new double[HIDDEN];
        for (int h = 0; h < HIDDEN; h++) {
            double z = b1[h];
            for (int i = 0; i < INPUT; i++)
                z += w1[h * INPUT + i] * input[i];
            hidden[h] = Math.tanh(z);
        }
        double[] outputs = new double[OUTPUT];
        for (int action = 0; action < OUTPUT; action++) {
            double z = b2[action];
            for (int h = 0; h < HIDDEN; h++)
                z += w2[action * HIDDEN + h] * hidden[h];
            if (!Double.isFinite(z))
                throw new IllegalArgumentException("Invalid model output");
            outputs[action] = z;
        }
        return outputs;
    }

    /**
     * Hard action mask: unreported sources cannot be selected even if weights
     * assign them large logits. WITHHELD is handled upstream before any
     * recipient report NBT read, then forced ABSTAIN.
     */
    public Action choose(double[] features) {
        double[] logits = scores(features);
        if (features[0] == 0.0 && features[5] == 0.0)
            return Action.ABSTAIN;
        if (features[0] == 0.0) logits[0] = Double.NEGATIVE_INFINITY;
        if (features[5] == 0.0) logits[1] = Double.NEGATIVE_INFINITY;
        int selected = 0;
        for (int i = 1; i < OUTPUT; i++)
            if (logits[i] > logits[selected]) selected = i;
        return Action.values()[selected];
    }

    /** A report is permitted to be uncertain; never silently fill missing data. */
    public static void encode(double[] features, int candidate,
                              int wheat, long deliveryAge, long observationAge,
                              int revision, boolean present) {
        if (features == null || features.length != INPUT || candidate < 0 || candidate > 1)
            throw new IllegalArgumentException("Wrong choice observation");
        int start = candidate * 5;
        for (int i = start; i < start + 5; i++) features[i] = 0.0;
        if (!present) return;
        if (wheat <= 0 || deliveryAge < 0 || deliveryAge > 200
                || observationAge < deliveryAge || observationAge > 240 || revision < 1)
            throw new IllegalArgumentException("Invalid fresh delivered report");
        features[start] = 1.0;
        features[start + 1] = Math.min(8, wheat) / 8.0;
        features[start + 2] = deliveryAge / 200.0;
        features[start + 3] = observationAge / 240.0;
        features[start + 4] = Math.min(16, revision) / 16.0;
    }
}
