package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;
import java.util.UUID;

/**
 * Durable tick bounds for attributing one machine observation to one operation.
 * Start is persisted before execution; completion is an idempotent append-only
 * record. Callers must supply authoritative server ticks, not client timestamps.
 */
public final class DurableObservationWindow {
    public record Window(UUID operationId, UUID citizenId, String machineKey, long startTick, long endTick) {}
    private final DurableOperationIntents starts;
    private final DurableCreditLedger endings;
    public DurableObservationWindow(Path startDir, Path completionDir) {
        starts = new DurableOperationIntents(Objects.requireNonNull(startDir));
        endings = new DurableCreditLedger(Objects.requireNonNull(completionDir));
    }
    private static String key(UUID operation) { return "observation-window/" + operation; }
    private static String encode(UUID citizen, String machine, long tick) {
        Objects.requireNonNull(citizen);
        if(machine==null || machine.isBlank() || machine.contains("|") || tick<0)
            throw new IllegalArgumentException("Invalid observation start");
        return citizen + "|" + machine + "|" + tick;
    }
    public void begin(UUID operation, UUID citizen, String machine, long startTick) throws IOException {
        Objects.requireNonNull(operation);
        var prepared=starts.prepare(key(operation),encode(citizen,machine,startTick));
        // The durable store permits only exact replay of the original start.
        if(!prepared.intent().evidence().equals(encode(citizen,machine,startTick)))
            throw new IOException("Conflicting start");
    }
    private Window start(UUID operation) throws IOException {
        var intent=starts.pending(key(operation)).orElseThrow(()->new IOException("Missing start"));
        String[] parts=intent.evidence().split("\\|",-1);
        if(parts.length!=3)throw new IOException("Corrupt observation start");
        try {
            return new Window(operation,UUID.fromString(parts[0]),parts[1],Long.parseLong(parts[2]),-1);
        }catch(IllegalArgumentException e){throw new IOException("Invalid start fields",e);}
    }
    public boolean complete(UUID operation,UUID citizen,String machine,long endTick) throws IOException {
        Window first=start(operation);
        if(!first.citizenId().equals(citizen) || !first.machineKey().equals(machine)
                || endTick<first.startTick())throw new IOException("Invalid observation completion");
        return endings.commit(new DurableCreditLedger.Credit(operation,citizen,1,
                first.machineKey()+"|"+first.startTick()+"|"+endTick));
    }
    public Window recovered(UUID operation) throws IOException {
        Window first=start(operation);
        var credit=endings.find(operation);
        if(credit.isEmpty())throw new IOException("Operation window incomplete: quarantine");
        var saved=credit.get();
        String expectedPrefix=first.machineKey()+"|"+first.startTick()+"|";
        if(!saved.beneficiary().equals(first.citizenId())||!saved.receipt().startsWith(expectedPrefix))
            throw new IOException("Window completion mismatch");
        try {
            long end=Long.parseLong(saved.receipt().substring(expectedPrefix.length()));
            if(end<first.startTick())throw new IOException("Invalid stored window");
            return new Window(operation,first.citizenId(),first.machineKey(),first.startTick(),end);
        }catch(NumberFormatException invalid){throw new IOException("Corrupt window end",invalid);}
    }
}
