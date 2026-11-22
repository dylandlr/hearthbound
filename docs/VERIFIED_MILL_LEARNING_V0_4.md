# Verified mill outcome to shadow value replay

This slice connects actual executor assignment and Create processing to the
existing OutcomeLedger proposal and an explicit numeric terminal value update.
It is an operator-triggered, disposable **success-only shadow experiment**.
It does not change citizen decisions, award spendable points, teach a recipe,
train the colony allocation network, or establish policy improvement.

## Repository baseline

Started from PR #200 (`cc2139108410756556ac474445d09dfa5465bb2a`), including
the scoped civilization v0.3 contracts from #196 and simulator diagnostics
#197–200. Those PRs were open, not merged, at inspection. #200 reports a
positive simulator pilot but explicitly rejects Minecraft promotion; scripted
allocation still leads. Its weights and action/observation contracts are unchanged.
The repository calls its live proposal layer `OutcomeLedger` and documents it
as v0.15.5; v0.3 refers to the civilization decision contracts, not a separate
OutcomeLedger implementation found during this audit.

## End-to-end operation

Run as an operator near the citizen who completed the mill job:

```text
sable mill-learning-probe <job-uuid>
```

Only a UUID is accepted; the operator cannot supply rewards, samples, ticks,
claim fields or model parameters. On the server thread the command:

1. Opens the world-bound, checksummed causal journal and joins the current
   villager assignment, Create callback, world/dimension, machine, chronology,
   and untainted held reservation. It reconciles recovered admission against
   current Minecraft witnesses. Unknown/foreign/unloaded/invalid evidence fails closed.
2. Independently re-exports the current Create claim and checks every claim
   field against that reconciled observation. A raw receipt or recovered
   `ADMITTED` state alone never admits a learning sample.
3. Registers the actual executor assignment in OutcomeLedger. The existing
   illustrative personal budget is 500 milli-points, colony/research zero.
   No durable payout method is called. This reward is a declared experimental
   objective; Minecraft does not itself generate reward points.
4. Replays one terminal sample from zero with fixed `alpha=0.25`,
   `gamma_per_tick=0.999`, `duration=finishTick-assignedTick`, and
   `target=0.5*gamma_per_tick^duration`. The update is
   `Q_after=Q_before+alpha*(target-Q_before)` for the executed haul action.
5. Returns identities, measured duration, reward, target and before/after values.
   No model survives the query, so duplicate queries cannot compound updates
   and later revoked evidence cannot retain a cached learned value.

The pure replay component also supports up to 128 independently revalidated
inputs for one citizen, deduplicates by event, rejects conflicting replay and
orders by finish tick/event ID. The live command deliberately supplies **one**
job: the existing executor NBT only proves the current completed assignment.
Do not manufacture historical assignment observations to increase sample count.

`shadow_learning_authorized=true` means only this disposable experimental
update ran. `learning_authorized=false` retains the existing gameplay/online
learning boundary; `policy_control=false`, `model_persisted=false`, and
`reward_authorized=false` make the operational limits explicit.

## Validation

- `bash scripts/test-research-journals.sh`: pure Java tests including analytic
  discount/update, deduplication, identity mismatch, real journal reopen and
  terminal revocation. Their receipt fixtures are synthetic, not live Minecraft.
- `python -m unittest discover -s scripts -p 'test_mill_learning_acceptance.py'`:
  independent numeric acceptance oracle, including rejection of zero/NaN/infinite
  updates, changed evidence, wrong duration, unauthorized control and cached denial.
- Existing real Create workflow runs `rcon_sable_first_mill.py`: actual wheat
  movement and Create callback, numeric update independently checked against the
  proposal's executor/process ticks, exact duplicate replay, unknown/foreign job
  denial, release/revocation denial with no value returned.
- Existing real outcome restart workflow saves the actual replay and requires
  the same revalidated update after stopping/restarting Forge, then revokes it.

Live validation must be reported from completed runs of this revision. Unit
tests and compiled Forge sources alone do not establish live acceptance.

## Next slice and limits

The current assignment is operator-issued. This validates learning plumbing,
not autonomous discovery or knowledge transfer. Success-only samples cannot
estimate expected return across failures, identify a better action, or justify
model deployment. No additional causal contributors are inferred.

Next: persist the pre-action local observation and policy-selected decision
with the existing world/session/revision contract, then collect both verified
success and genuine terminal failure outcomes. Define an explicit live
observation/action mapping and Python/Java inference parity before connecting
these samples to the colony learner. Evaluate frozen policies on matched,
held-out Minecraft runs before any behavior promotion. Teaching additionally
needs a recipient knowledge event and an observed downstream decision.
