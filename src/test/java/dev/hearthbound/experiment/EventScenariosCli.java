package dev.hearthbound.experiment;

import java.nio.file.Files;
import java.nio.file.Path;

/** Bounded test bridge. Not a native administration or physical injection command. */
public final class EventScenariosCli {
    private static byte[] read(String path, int limit) throws Exception {
        try (var input = Files.newInputStream(Path.of(path))) {
            byte[] data = input.readNBytes(limit + 1);
            if (data.length > limit) throw new IllegalArgumentException("scenario input exceeds byte bound");
            return data;
        }
    }
    private static void identity(EventScenarios.Scenario scenario) {
        System.out.println("MANIFEST_SHA256\t" + scenario.manifestDigest());
        System.out.println("RUN_ID\t" + scenario.journalRunId());
        System.out.println("SCHEDULE_SHA256\t" + scenario.schedule().digest());
        System.out.println("TRIAL\t" + scenario.trialId());
        System.out.println("EVENT_COUNT\t" + scenario.schedule().events().size());
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 5 && args[0].equals("generate")) {
            var config = EventScenarios.Config.fromBytes(read(args[1], EventScenarios.MAX_CONFIG_BYTES));
            var scenario = EventScenarios.generate(config, Long.parseLong(args[2]), EventScenarios.Mode.fromWire(args[3]), args[4]);
            System.out.write(scenario.manifest());
            return;
        }
        if (args.length < 2) throw new IllegalArgumentException("command manifest [journal world tick]");
        var scenario = EventScenarios.fromManifest(read(args[1], EventScenarios.MAX_MANIFEST_BYTES));
        switch (args[0]) {
            case "roundtrip" -> {
                if (args.length != 2) throw new IllegalArgumentException("unexpected arguments");
                System.out.write(scenario.manifest());
            }
            case "identity" -> {
                if (args.length != 2) throw new IllegalArgumentException("unexpected arguments");
                identity(scenario);
            }
            case "journal-create", "journal-status", "journal-poll" -> {
                int expected = args[0].equals("journal-poll") ? 5 : 4;
                if (args.length != expected) throw new IllegalArgumentException("invalid journal arguments");
                try (var scheduler = args[0].equals("journal-create") ? scenario.createScheduler(Path.of(args[2]), args[3])
                                                                    : scenario.openScheduler(Path.of(args[2]), args[3])) {
                    if (args[0].equals("journal-poll")) scheduler.poll(Long.parseLong(args[4]));
                    identity(scenario);
                    System.out.println("CURSOR\t" + scheduler.clock());
                    System.out.println("NEXT\t" + scheduler.nextIndex());
                    var pending = scheduler.pending();
                    System.out.println("PENDING\t" + (pending == null ? "-" : pending.transition().transitionId() + "\t" + pending.recoveryRequired()));
                }
            }
            default -> throw new IllegalArgumentException("unknown scenario test command");
        }
    }
}
