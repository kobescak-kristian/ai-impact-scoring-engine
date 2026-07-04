# ADR 0001: Compute impact scores deterministically, before the AI layer runs

## Status
Accepted

## Date: 2026-07-04

## Context
The engine turns a lead's (decision, outcome) pair into a financial impact figure, then
asks an LLM to interpret the aggregated results. A decision was needed on where the
line sits between "fixed logic" and "AI judgment" — specifically, whether the LLM should
see raw lead records and reason about financial impact itself, or only receive
already-computed numbers.

## Decision
Score computation is entirely rule-based and runs before any AI call:

- `pipeline/router.py` maps every valid `(decision, outcome)` pair to an `impact_type`
  via a static lookup table (`IMPACT_ROUTING_TABLE`) — no model involved.
- `pipeline/outcome_handler.py` (`compute_lead_impact`) converts each `impact_type` into
  a `financial_impact` using fixed multipliers from `config/settings.py`
  (`false_positive_cost_multiplier`, `delayed_conversion_penalty`,
  `missed_opportunity_multiplier`).
- `pipeline/impact_evaluator.py` (`evaluate_impact`) aggregates all per-lead impacts into
  an `ImpactMetrics` object. This module imports no LLM client.
- `pipeline/impact_analyzer.py` (`analyze_impact`) is the only module that calls an LLM.
  Its function signature takes `ImpactMetrics` only — it has no access to individual
  lead records, decisions, or outcomes.

## Consequences
- Financial numbers are fully reproducible and auditable — the same input always
  produces the same `financial_impact`, independent of LLM variance.
- The LLM cannot fabricate or alter a dollar figure; it can only narrate numbers it's
  handed, which bounds hallucination risk to prose (summary/issues/recommendations),
  not to the metrics themselves.
- Cost model accuracy is capped by the fixed multipliers (15% / 10% / 100%) in
  `config/settings.py` — already flagged in README's Known Limitations as
  uncalibrated against real sales-cycle costs.
- Adding a new decision/outcome combination requires a code change to
  `IMPACT_ROUTING_TABLE`, not a config change — routing logic is not currently
  data-driven.
