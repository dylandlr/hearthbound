package dev.hearthbound.civilization;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.ServiceValueLearner.*;

public final class FrozenServicePolicyTest {
    static void check(boolean b) { if (!b) throw new AssertionError(); }
    static void reject(Runnable r) {
        try { r.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("Invalid model/menu admitted");
    }
    static String hash(byte[] bytes) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    public static void main(String[] args) throws Exception {
        Path root = Path.of("src/main/resources/data/hearthbound/policies");
        byte[] bytes = Files.readAllBytes(root.resolve("service-trained-v0-22.txt"));
        String expected = Files.readString(root.resolve("service-trained-v0-22.txt.sha256")).trim();
        var model = FrozenServicePolicy.parse(bytes, expected);
        int examples = 0;
        for (String line : Files.readAllLines(Path.of("docs/evidence/shared-service-learning-v0-22/parity.tsv"))) {
            double[] values = Arrays.stream(line.split("\t")).mapToDouble(Double::parseDouble).toArray();
            check(values.length == 31);
            check(Math.abs(model.value(Arrays.copyOf(values, 30)) - values[30]) < 1e-10); examples++;
        }
        check(examples >= 20); check(model.sha256().equals(expected));
        reject(() -> FrozenServicePolicy.parse(bytes, "0".repeat(64)));
        byte[] wrongShape = new String(bytes, StandardCharsets.US_ASCII).replace(" 30 32 16 1\n", " 31 32 16 1\n").getBytes(StandardCharsets.US_ASCII);
        String wrongHash = hash(wrongShape); reject(() -> FrozenServicePolicy.parse(wrongShape, wrongHash));
        String text = new String(bytes, StandardCharsets.US_ASCII);
        int first = text.indexOf("w1 ") + 3, end = text.indexOf(' ', first);
        byte[] nonfinite = (text.substring(0, first) + "NaN" + text.substring(end)).getBytes(StandardCharsets.US_ASCII);
        String nonfiniteHash = hash(nonfinite); reject(() -> FrozenServicePolicy.parse(nonfinite, nonfiniteHash));
        var citizen = UUID.randomUUID();
        Candidate supply = new Candidate("s", citizen, UUID.randomUUID(), null, Kind.SUPPLY_WHEAT,
            ServiceValueLearner.features(Kind.SUPPLY_WHEAT, 64, 90, 600, 0, .75), 3);
        Candidate wait = new Candidate("w", citizen, null, null, Kind.WAIT,
            ServiceValueLearner.features(Kind.WAIT, 0, 0, 0, 0, .5), 0);
        double[][] inputs = FrozenServicePolicy.encode(List.of(supply, wait));
        check(inputs[0][11] == .5 && inputs[0][21] == 1 && inputs[1][11] == .5);
        check(inputs[0][0] == 1 && inputs[0][6] == 1 && inputs[1][9] == 1);
        double[][] reversed = FrozenServicePolicy.encode(List.of(wait, supply));
        check(Arrays.equals(inputs[0], reversed[1])); check(Arrays.equals(inputs[1], reversed[0]));
        reject(() -> FrozenServicePolicy.encode(List.of()));
        reject(() -> FrozenServicePolicy.encode(List.of(supply, supply)));
        Candidate foreign = new Candidate("f", UUID.randomUUID(), null, null, Kind.WAIT, wait.features(), 0);
        reject(() -> FrozenServicePolicy.encode(List.of(supply, foreign)));
        reject(() -> model.value(new double[29]));
        var scope = new NeedServiceKernel.Scope(UUID.randomUUID(), "minecraft:overworld");
        var observation = new ServiceOutcome(UUID.randomUUID(), scope, UUID.randomUUID(), citizen, null,
            Kind.CARRY_REQUEST, null, ServiceValueLearner.features(Kind.CARRY_REQUEST, 2, 10, 0, 0, .5),
            1, 5, .1, Outcome.VERIFIED_SOURCE_OBSERVATION);
        check(observation.outcome().completed());
        reject(() -> new ServiceOutcome(UUID.randomUUID(), scope, UUID.randomUUID(), citizen, null,
            Kind.WAIT, null, wait.features(), 1, 5, .1, Outcome.VERIFIED_SOURCE_OBSERVATION));
        System.out.println("PASS FrozenServicePolicyTest: " + examples + " Python/Java forward-pass cases, private menus, integrity, typed source observation");
    }
}
