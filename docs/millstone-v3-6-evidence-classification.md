# v3.6 — Distinguishing actual observed output from missing evidence

The processing-boundary mutation audit now classifies output observations as:

- `positive_deltas`: at least one output slot increased in count or was populated, without any incompatible slot replacement.
- `none_observed`: input shrank exactly one but no positive slot delta was observed.
- `ambiguous`: an output slot changed between incompatible nonempty item stacks, so attribution from end-state differences is impossible.

All three remain `evidence=diagnostic_only researchCredit=false`. Even `positive_deltas` is not a durable research receipt, as neither recipe identity nor crash-safe event persistence is implemented. The audit never rerolls outputs or manipulates Create inventories.

Source investigation indicates that Create's private processing method performs input shrink and output insertion within the same function; this hook surrounds that method. A runtime GameTest must verify injection and logs before enabling journal ingestion.

Successful prior CI: https://github.com/dylandlr/hearthbound/actions/runs/39866287465. This documentation and the associated audit changes require a subsequent CI verification.
