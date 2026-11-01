package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;

/**
 * Owns the existing attributed inbox / durable ledger pair in the server process.
 * No reward is delivered without an explicitly supplied admitted claim. 
 * Server thread only; world headers and rollback checks are required before opening.
 */
public final class ResearchJournalRuntime implements AutoCloseable {
    private final AttributedMillInbox inbox;
    private final DurableRewardLedger ledger;
    private boolean closed;

    public ResearchJournalRuntime(Path inboxFile, Path ledgerFile) throws IOException {
        Objects.requireNonNull(inboxFile);
        Objects.requireNonNull(ledgerFile);
        inbox = new AttributedMillInbox(inboxFile);
        DurableRewardLedger opened;
        try { opened = new DurableRewardLedger(ledgerFile); }
        catch (IOException | RuntimeException e) {
            try { inbox.close(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
            throw e;
        }
        ledger = opened;
    }

    /**
     * Caller MUST independently verify world identity, rollback state, and
     * untainted Create evidence immediately before invoking this method.
     */
    public synchronized boolean enqueue(VerifiedMillAttribution.Claim claim) throws IOException {
        requireOpen();
        Objects.requireNonNull(claim);
        return inbox.enqueue(new AttributedMillInbox.Entry(
            claim.eventId(), claim.citizenId(), claim.jobId(), claim.dimension(),
            claim.machine(), claim.observedStartTick(), claim.finishTick()));
    }

    /**
     * This is intentionally NOT available as a production operation yet:
     * the reward journal has no authoritative world-ID header or late-taint reconciliation.
     */
    public synchronized void drainUnsafeForStandaloneTestsOnly() throws Exception {
        requireOpen();
        ResearchReceiptDelivery.drain(inbox, ledger, true);
    }

    public synchronized int pendingCount() { requireOpen(); return inbox.pendingCount(); }
    public synchronized long researchMilliPoints(String citizen) {
        requireOpen();
        return ledger.total(citizen, "research");
    }
    private void requireOpen() { if (closed) throw new IllegalStateException("closed"); }
    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        IOException failure = null;
        try { inbox.close(); } catch (IOException e) { failure = e; }
        try { ledger.close(); } catch (IOException e) {
            if (failure == null) failure = e; else failure.addSuppressed(e);
        }
        if (failure != null) throw failure;
    }
}
