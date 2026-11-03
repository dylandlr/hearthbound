# v0.8.6 — Explicit neural/scripted shadow selection

Adds a **read-only** live Minecraft `/hearthbound policy_shadow <mill> <mode>` command.
Modes: `SCRIPTED`, `TRAINED_MLP`.

The command obtains the same server-side millstone and citizen observations as `policy_probe`, checks the bundled neural model checksum, and returns:
- `shadow_mode` and `selected_action`
- `mlp_action` (raw trained-network result)
- `model_disagreement` versus reference policy
- `action_masked` if the model proposed an impossible action
- `EXECUTION_DISABLED` so commands never operate machinery

The model is a synthetic **imitation-trained** network and does not learn from Sable's persisted experience merely because experience is an input. This tiny 5-feature millstone interface is not the full agent observation contract and does not measure policy improvement or support autonomous task execution.

Tested in CI only once both Java parity/action-mask checks and the Forge dedicated-server smoke test pass. The live smoke now asks both modes for a suggestion on the same powered millstone before wheat enters it.

**Next acceptance**: record disagreements under distinct real Minecraft states, export immutable model hashes in run metadata, then run a controlled action-execution A/B with task outcome and safety checks. Do not enable autonomous model-selected actions until execution-time reservations and inventory checks are trusted.
