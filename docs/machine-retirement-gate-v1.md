# Machine claim retirement eligibility v1

Following successful real Forge acceptance of exclusive machine ownership (run 40175218344), the next boundary is an explicit fail-closed retirement gate.

`MachineClaimRetirementGate` returns eligibility **only** if the recovered claim's operation and citizen match, the operation receipt, citizen credit and machine checkpoint are durable, the machine is idle, the wheat transfer has been reconciled and no conflicting evidence exists. Null or incomplete proof keeps the claim. Ten standalone checks cover acceptance and denial conditions.

This is **not claim release**. A separate crash-safe, machine-keyed ledger must atomically record retirement and acquisition of the next claim; do not delete the existing .intent file on eligibility alone. The existing durable intent storage deliberately has no retirement API. Real Minecraft machine replay/recovery tests must precede authorizing handoff in a live colony.

No autonomous NPC or policy-driven navigation exists yet.
