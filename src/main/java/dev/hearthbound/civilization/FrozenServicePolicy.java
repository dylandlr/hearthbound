package dev.hearthbound.civilization;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;

/** Frozen shared candidate network. No world, inventory, peer or training access. */
public final class FrozenServicePolicy {
    public static final String SCHEMA = "hearthbound.private-service-menu.v0.22";
    public static final String HEADER = "HEARTHBOUND_SERVICE_DDQN_V1 " + SCHEMA + " 30 32 16 1";
    private static final int[] SIZES = {960, 32, 512, 16, 16, 1};
    private static final String[] NAMES = {"w1", "b1", "w2", "b2", "w3", "b3"};
    private final double[][] tensors;
    private final String sha256;

    private FrozenServicePolicy(double[][] tensors, String sha256) {
        this.tensors = tensors; this.sha256 = sha256;
    }
    public String sha256() { return sha256; }

    public static FrozenServicePolicy parse(byte[] bytes, String expectedSha256) {
        if (bytes.length > 100000 || expectedSha256 == null || !expectedSha256.matches("[0-9a-f]{64}"))
            throw new IllegalArgumentException("Invalid checkpoint bounds/hash");
        String actual;
        try { actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
        if (!actual.equals(expectedSha256)) throw new IllegalArgumentException("Checkpoint hash mismatch");
        String[] lines = new String(bytes, StandardCharsets.US_ASCII).split("\\n");
        if (lines.length != 7 || !HEADER.equals(lines[0])) throw new IllegalArgumentException("Checkpoint schema mismatch");
        double[][] tensors = new double[6][];
        for (int t = 0; t < 6; t++) {
            String[] tokens = lines[t + 1].split(" ", -1);
            if (tokens.length != SIZES[t] + 1 || !NAMES[t].equals(tokens[0]))
                throw new IllegalArgumentException("Checkpoint tensor shape mismatch");
            tensors[t] = new double[SIZES[t]];
            for (int i = 0; i < SIZES[t]; i++) {
                double v = Double.parseDouble(tokens[i + 1]);
                if (!Double.isFinite(v) || Math.abs(v) > 1000) throw new IllegalArgumentException("Invalid checkpoint value");
                tensors[t][i] = v;
            }
        }
        return new FrozenServicePolicy(tensors, actual);
    }

    public static FrozenServicePolicy resource(boolean trained) {
        String path = "/data/hearthbound/policies/service-" + (trained ? "trained" : "untrained") + "-v0-22.txt";
        try (InputStream weights = FrozenServicePolicy.class.getResourceAsStream(path);
             InputStream hash = FrozenServicePolicy.class.getResourceAsStream(path + ".sha256")) {
            if (weights == null || hash == null) throw new IllegalStateException("Missing frozen service checkpoint");
            return parse(weights.readNBytes(100001), new String(hash.readNBytes(128), StandardCharsets.US_ASCII).trim());
        } catch (IOException failure) { throw new IllegalStateException("Cannot read service checkpoint", failure); }
    }

    public static double[][] encode(List<ServiceValueLearner.Candidate> menu) {
        if (menu.isEmpty() || menu.size() > 73) throw new IllegalArgumentException("Invalid private menu size");
        double[] mean = new double[10], max = new double[10];
        var owner = menu.get(0).citizen();
        var ids = new java.util.HashSet<String>();
        for (var c : menu) {
            if (!c.citizen().equals(owner) || !ids.add(c.id())) throw new IllegalArgumentException("Mixed-owner or duplicate menu");
            for (int j = 0; j < 10; j++) {
                double value = c.features().values().get(j);
                mean[j] += value; max[j] = Math.max(max[j], value);
            }
        }
        for (int j = 0; j < 10; j++) mean[j] /= menu.size();
        double[][] result = new double[menu.size()][30];
        for (int i = 0; i < menu.size(); i++) for (int j = 0; j < 10; j++) {
            result[i][j] = menu.get(i).features().values().get(j);
            result[i][10 + j] = mean[j]; result[i][20 + j] = max[j];
        }
        return result;
    }

    public double value(double[] input) {
        if (input.length != 30) throw new IllegalArgumentException("Invalid policy input length");
        for (double v : input) if (!Double.isFinite(v) || v < 0 || v > 1)
            throw new IllegalArgumentException("Invalid policy input value");
        double[] h1 = layer(input, tensors[0], tensors[1], 32, true);
        double[] h2 = layer(h1, tensors[2], tensors[3], 16, true);
        double value = layer(h2, tensors[4], tensors[5], 1, false)[0];
        if (!Double.isFinite(value)) throw new IllegalStateException("Nonfinite frozen prediction");
        return value;
    }

    private static double[] layer(double[] input, double[] weights, double[] bias, int width, boolean relu) {
        double[] output = bias.clone();
        for (int i = 0; i < input.length; i++) for (int j = 0; j < width; j++) output[j] += input[i] * weights[i * width + j];
        if (relu) for (int j = 0; j < width; j++) output[j] = Math.max(0, output[j]);
        return output;
    }
}
