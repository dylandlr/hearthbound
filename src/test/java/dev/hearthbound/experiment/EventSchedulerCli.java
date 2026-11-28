package dev.hearthbound.experiment;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Test bridge for cross-language contracts, not a Minecraft administration command. */
public final class EventSchedulerCli {
    private static List<EventScheduler.Event> events(Path path) throws Exception {
        var result = new ArrayList<EventScheduler.Event>();
        for (String line : Files.readAllLines(path, StandardCharsets.US_ASCII)) {
            if (line.isBlank() || line.startsWith("#")) continue;
            String[] fields = line.split("\t", -1);
            if (fields.length != 5) throw new IllegalArgumentException("events.tsv requires five fields");
            result.add(new EventScheduler.Event(fields[0], fields[1], Long.parseLong(fields[2]),
                Long.parseLong(fields[3]), Double.parseDouble(fields[4])));
        }
        return result;
    }
    private static Long tick(String text) { return text.equals("-") ? null : Long.valueOf(text); }
    private static String identity(EventScheduler scheduler, String text) {
        return text.startsWith("@") ? scheduler.transitionId(Integer.parseInt(text.substring(1))) : text;
    }
    private static void status(EventScheduler scheduler) {
        System.out.println("DIGEST\t" + scheduler.schedule().digest());
        System.out.println("CLOCK\t" + scheduler.clock());
        System.out.println("NEXT\t" + scheduler.nextIndex());
        var pending = scheduler.pending();
        if (pending == null) System.out.println("PENDING\t-");
        else {
            var t = pending.transition();
            System.out.println("PENDING\t" + t.index() + "\t" + t.transitionId() + "\t" + t.phase()
                + "\t" + t.tick() + "\t" + pending.observedTick() + "\t" + t.kind()
                + "\t" + EventScheduler.severityBits(t.severity()) + "\t" + pending.recoveryRequired());
        }
        for (var r : scheduler.receipts()) System.out.println("RECEIPT\t" + r.index() + "\t" + r.transitionId()
            + "\t" + r.outcome() + "\t" + r.evidenceId() + "\t" + (r.effectTick() == null ? "-" : r.effectTick())
            + "\t" + r.mode());
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2 && args[0].equals("digest")) {
            System.out.println(new EventScheduler.Schedule(events(Path.of(args[1]))).digest());
            return;
        }
        if (args.length < 5) throw new IllegalArgumentException("command journal events.tsv world run [arguments]");
        String command = args[0];
        var events = events(Path.of(args[2]));
        boolean create = command.equals("create") || command.equals("script");
        try (var scheduler = create ? EventScheduler.create(Path.of(args[1]), events, args[3], args[4])
                                   : EventScheduler.open(Path.of(args[1]), events, args[3], args[4])) {
            switch (command) {
                case "create", "status" -> {
                    if (args.length != 5) throw new IllegalArgumentException("unexpected arguments");
                }
                case "poll" -> {
                    if (args.length != 6) throw new IllegalArgumentException("poll requires tick");
                    scheduler.poll(Long.parseLong(args[5]));
                }
                case "reconcile", "ack" -> {
                    if (args.length != 9) throw new IllegalArgumentException("settlement requires identity outcome evidence effect-tick");
                    if (command.equals("reconcile")) scheduler.reconcile(identity(scheduler, args[5]), EventScheduler.Outcome.valueOf(args[6]), args[7], tick(args[8]));
                    else scheduler.acknowledge(identity(scheduler, args[5]), EventScheduler.Outcome.valueOf(args[6]), args[7], tick(args[8]));
                }
                case "hold" -> {
                    if (args.length != 5) throw new IllegalArgumentException("unexpected arguments");
                    System.out.println("LOCKED");
                    System.out.flush();
                    System.in.read();
                    return;
                }
                case "script" -> {
                    if (args.length != 6) throw new IllegalArgumentException("script requires commands.tsv");
                    for (String line : Files.readAllLines(Path.of(args[5]), StandardCharsets.US_ASCII)) {
                        if (line.isBlank() || line.startsWith("#")) continue;
                        String[] fields = line.split("\t", -1);
                        if (fields[0].equals("POLL") && fields.length == 2) scheduler.poll(Long.parseLong(fields[1]));
                        else if (fields[0].equals("ACK") && fields.length == 5)
                            scheduler.acknowledge(identity(scheduler, fields[1]), EventScheduler.Outcome.valueOf(fields[2]), fields[3], tick(fields[4]));
                        else if (fields[0].equals("RECONCILE") && fields.length == 5)
                            scheduler.reconcile(identity(scheduler, fields[1]), EventScheduler.Outcome.valueOf(fields[2]), fields[3], tick(fields[4]));
                        else throw new IllegalArgumentException("invalid script command");
                    }
                }
                default -> throw new IllegalArgumentException("unknown command");
            }
            status(scheduler);
        }
    }
}
