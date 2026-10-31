# Scripted milling baseline v0

A first deterministic policy now chooses among PREPARE_MILLING, WAIT, and ABORT from a bounded snapshot: assigned, wheat present, millstone present, motor present, dangerous, and already credited. No hidden knowledge, client-origin events, or learned weights are supplied.

The real Create motor GameTest requests the policy decision before placing a creative motor. It fails if the authorized fixture does not choose PREPARE_MILLING, and the log verifier requires exactly one decision marker. The GameTest itself still installs and operates the fixture machine; this is **not** an embodied AI citizen.

The next step is a server-owned work-order executor with a state machine for approaching, loading inputs, enabling power, observing results, and reporting to the research ledger. Later the scripted decision can be replaced by an MLP policy under identical observation/action contracts.
