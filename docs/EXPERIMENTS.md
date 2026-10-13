# Colony Intelligence Experiments v0.1

## Primary question
How does decision policy type affect settlement development, reliability, productivity, resilience and player experience when the world and allowed actions are held constant?

## Initial benchmark
First Mill: three citizens, one approved mill workflow, limited wheat, input/output inventories, one worker trained in milling. Each policy chooses among equivalent structured jobs. World engine and action executor are shared.

### Scenarios
1. Baseline: maintain wheat milling throughput.
2. Scarcity: shortfall in wheat.
3. Blockage: output inventory becomes full.
4. Labor shock: trained operator temporarily unavailable.
5. Restart: interrupt during carrying/processing/delivery and reconcile exactly.
6. Coordination: player departs while autonomous work continues.

### Outcomes
- Net flour delivered and accepted batches.
- Resources consumed and destroyed/lost; inventory invariants.
- Useful work per citizen-minute.
- Time to diagnose and recover from blockage.
- Unfinished jobs; retries; invalid actions; policy inference time.
- Skill growth and transfer (once mentorship exists).
- Later: colony size, well-being, specialization, projects, fairness, trade and player fun metrics.

### Trial design
Use fixed paired world seeds, scenario configurations and evaluation horizons. Keep held-out seeds separate from training data. Run multiple replicated trials and report confidence intervals/distributions, not just a best run. Track policy versions, training datasets, prompts, tokens and hardware. Evaluate statistical and gameplay significance separately.

### Fairness limitations
LLM policies may receive textual rendering of the same structured observations but not hidden world state. Restrict model-specific feature engineering or report it as a separate treatment. RL trained on many simulated episodes is not directly cost-equivalent to an untrained baseline; report training compute separately.

### Gameplay comparison
A policy that optimizes milling throughput might be bad at being a memorable villager. Evaluate social behavior and game enjoyment separately, rather than treating efficiency as the only objective.
