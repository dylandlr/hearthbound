# Hearthbound v2.4 — Research Observatory figures (prototype)

Open `dashboard/research-observatory.html` directly in a browser (no server or CDN required). Select a `simulation-results/summary.json` or `benchmark/aggregate.json` artifact from the existing GitHub Actions simulation harness.

The standalone dashboard includes:
- trial count, pass fraction, mean game ticks to verified hypothesis, mean wheat consumption;
- milestone chart: proposal, haul, first physical flour, confirmed hypothesis (Minecraft game ticks);
- trial outcomes by world seed;
- evidence table with explicit missing measurements;
- mobile-responsive layout and basic accessible labels.

All displayed performance values come from supplied JSON. No fake data, inferred internal rationale, simulated research outcomes, or unverified gameplay footage. The aggregate runner's mean values are recalculated from per-trial records for consistency. The provided JSON is processed locally and is not uploaded to a service.

This is a **research UI prototype**, not a modded Minecraft HUD. The existing repository is primarily Java/Python with no front-end application. Future version should add actual decision-trace data (observation vector, action mask, chosen policy, per-action scores, rewards, counterfactuals), pairwise policy-payoff heatmaps with uncertainty, regret/CCE convergence and behavioral comparison. These require instrumenting the gameplay events, not inventing scores.
