package dev.hearthbound.evidence;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Pure Java parse, checksum, bounded-feature and hard-action-mask tests. */
public final class ReportChoiceMlpTest {
    private static int checks;
    private static void yes(boolean actual) {
        checks++;
        if (!actual) throw new AssertionError("Frozen report MLP test " + checks);
    }
    private static void rejects(Throwing test) {
        boolean failed = false;
        try { test.run(); } catch (Exception expected) { failed = true; }
        yes(failed);
    }
    @FunctionalInterface private interface Throwing { void run() throws Exception; }
    private static String vector(int len) {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < len; i++) {
            if (i > 0) out.append(',');
            out.append('0');
        }
        return out.toString();
    }
    private static String modelText() {
        return String.join("\n",
            ReportChoiceMlp.SCHEMA,
            "origin=" + ReportChoiceMlp.ORIGIN,
            "training_seed=20261107", "training_samples=18000",
            "heldout_seed=20361107",
            "features=" + ReportChoiceMlp.FEATURES,
            "dimensions=10,16,3",
            "w1=" + vector(160),
            "b1=" + vector(16),
            "w2=" + vector(48),
            "b2=0.3,0.5,0.1") + "\n";
    }
    private static void save(Path file, Path sha, String content) throws Exception {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        Files.write(file, bytes);
        Files.writeString(sha, HexFormat.of().formatHex(
            MessageDigest.getInstance("SHA-256").digest(bytes)) + "\n");
    }
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("hearthbound-report-mlp-");
        Path file = dir.resolve("model.txt"), sha = dir.resolve("model.sha256");
        save(file, sha, modelText());
        ReportChoiceMlp mlp = ReportChoiceMlp.load(file, sha);
        yes(mlp.sha256().matches("[a-f0-9]{64}"));
        double[] x = new double[ReportChoiceMlp.INPUT];
        yes(mlp.choose(x) == ReportChoiceMlp.Action.ABSTAIN);
        ReportChoiceMlp.encode(x, 0, 4, 10, 15, 3, true);
        yes(x[0] == 1 && x[1] == 0.5);
        yes(x[2] == .05);
        yes(x[3] == 15.0 / 240.0);
        yes(x[4] == 3.0 / 16.0);
        yes(mlp.choose(x) == ReportChoiceMlp.Action.SOURCE_A);
        ReportChoiceMlp.encode(x, 1, 2, 0, 5, 2, true);
        yes(mlp.choose(x) == ReportChoiceMlp.Action.SOURCE_B);
        ReportChoiceMlp.encode(x, 1, 0, 0, 0, 0, false);
        yes(mlp.choose(x) == ReportChoiceMlp.Action.SOURCE_A);
        ReportChoiceMlp.encode(x, 0, 0, 0, 0, 0, false);
        yes(mlp.choose(x) == ReportChoiceMlp.Action.ABSTAIN);
        rejects(() -> ReportChoiceMlp.encode(x, 0, 1, 201, 220, 1, true));
        rejects(() -> ReportChoiceMlp.encode(x, 0, 1, 10, 9, 1, true));
        rejects(() -> ReportChoiceMlp.encode(x, 0, 0, 0, 0, 1, true));
        rejects(() -> ReportChoiceMlp.encode(x, 0, 1, 0, 0, 0, true));
        rejects(() -> ReportChoiceMlp.encode(x, 0, 1, 0, 241, 1, true));
        rejects(() -> mlp.scores(new double[9]));
        double[] bad = new double[10];
        bad[2] = Double.NaN;
        rejects(() -> mlp.scores(bad));
        bad[2] = Double.POSITIVE_INFINITY;
        rejects(() -> mlp.choose(bad));
        bad[2] = -0.1;
        rejects(() -> mlp.choose(bad));
        bad[2] = 1.1;
        rejects(() -> mlp.choose(bad));

        String original = modelText();
        Files.writeString(file, original.replace("b2=0.3,0.5,0.1", "b2=0.5,0.3,0.1"));
        rejects(() -> ReportChoiceMlp.load(file, sha)); // tamper without new SHA
        save(file, sha, original.replace("origin=" + ReportChoiceMlp.ORIGIN,
                                         "origin=ACTUAL_MINECRAFT_OUTCOMES"));
        rejects(() -> ReportChoiceMlp.load(file, sha)); // re-hashed provenance forgery
        save(file, sha, original.replace("dimensions=10,16,3", "dimensions=10,12,3"));
        rejects(() -> ReportChoiceMlp.load(file, sha));
        save(file, sha, original.replace("w2=" + vector(48), "w2=0"));
        rejects(() -> ReportChoiceMlp.load(file, sha));
        save(file, sha, original.replace("b2=0.3,0.5,0.1", "b2=0.3,NaN,0.1"));
        rejects(() -> ReportChoiceMlp.load(file, sha));
        System.out.println("ReportChoiceMlpTest: " + checks
            + " checks passed (frozen SHA; action mask; no world or training APIs)");
    }
}
