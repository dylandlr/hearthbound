# Hearthbound v2.5 — Research Decision Comparison

Adds `ResearchDecisionComparison.evaluate(observation)`, a pure Java paired evaluation of SCRIPTED and PERSONALITY research policies on the **same partially observed state**. It records each policy's candidate/action/utility, whether actions disagree, and an explicitly rule-derived explanation. This diagnostic evaluation does not act on the world or alter claims, machine processing, research evidence or knowledge.

The comparison is deterministic. Unit tests show (a) personality differences can cross an experiment threshold while the scripted baseline proposes and (b) no physically eligible candidate forces both to defer.

This is **counterfactual evaluation of policy decisions**, not a counterfactual rollout of long-term Minecraft outcomes. There is still no persistent decision trace export or live dashboard integration in this slice. The dashboard in v2.4 remains a real-metric viewer. Next: persist bounded versioned decision traces per citizen, expose a read-only RCON/JSON export, then integrate action-score figures into the dashboard. LLM explanations are not part of this system.
