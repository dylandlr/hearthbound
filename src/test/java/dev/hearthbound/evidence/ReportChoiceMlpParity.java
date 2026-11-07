package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Verify exact frozen Python MLP against Java float64 inference and hard masks. */
public final class ReportChoiceMlpParity {
    private ReportChoiceMlpParity() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException(
            "Usage: ReportChoiceMlpParity model.txt sha256.txt parity.tsv");
        ReportChoiceMlp model = ReportChoiceMlp.load(Path.of(args[0]), Path.of(args[1]));
        List<String> lines = Files.readAllLines(Path.of(args[2]));
        if (lines.size() < 65 || !lines.get(0).equals(
                "schema=hearthbound.report-mlp-python-java-parity.v1"))
            throw new AssertionError("Missing Python-generated parity fixtures");
        int cases = 0;
        for (int i = 1; i < lines.size(); i++) {
            String[] parts = lines.get(i).split("\t", -1);
            if (parts.length != 3) throw new AssertionError("Bad parity row " + i);
            String[] inputText = parts[0].split(",", -1);
            String[] scoreText = parts[1].split(",", -1);
            if (inputText.length != ReportChoiceMlp.INPUT
                    || scoreText.length != ReportChoiceMlp.OUTPUT)
                throw new AssertionError("Bad parity tensor width");
            double[] input = new double[ReportChoiceMlp.INPUT];
            for (int j = 0; j < input.length; j++) input[j] = Double.parseDouble(inputText[j]);
            double[] actual = model.scores(input);
            for (int j = 0; j < actual.length; j++) {
                double expected = Double.parseDouble(scoreText[j]);
                if (!Double.isFinite(expected) || Math.abs(expected - actual[j]) > 1.0e-8)
                    throw new AssertionError("Python/Java score mismatch row=" + i
                        + " action=" + j + " expected=" + expected + " actual=" + actual[j]);
            }
            var predicted = model.choose(input);
            if (!predicted.name().equals(parts[2]))
                throw new AssertionError("Python/Java chosen action mismatch at row=" + i);
            cases++;
        }
        System.out.println("REPORT_FROZEN_MLP_PYTHON_JAVA_PARITY_PASS cases=" + cases
            + " weights_sha256=" + model.sha256()
            + " no_minecraft_truth=true no_task_credit=true");
    }
}
