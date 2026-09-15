# AI Impact Scoring Engine: agent guide

Pointer-first router for coding agents working in this repository. It names
the files that own each fact; it does not replace them.

## Repository purpose

AI Impact Scoring Engine is a decision-intelligence and financial-impact
evaluation layer that sits on top of an existing lead-routing pipeline. It:

- accepts routing decisions that were already made, together with their
  observed outcomes;
- validates records on the supported load paths before they are stored;
- maps every decision/outcome combination to a deterministic impact class;
- computes per-record and aggregate financial impact with explicit logic and
  the configured financial multipliers;
- passes the aggregate metrics to an interpretation layer (an LLM, or a
  rule-based simulation);
- returns analysis and recommendations alongside the metrics, through a
  command-line demo and an HTTP API.

It does not make the upstream business routing decision. It evaluates
decisions made elsewhere.

## Authority and conflict handling

Each surface is authoritative for one kind of fact:

| Surface | Authoritative for |
|---|---|
| `README.md` | Public description, claims, known limitations, and the Version Log (the documented history surface) |
| `adr/0001-deterministic-scoring-before-ai-layer.md` | The material architecture decision separating deterministic scoring from AI interpretation |
| `config/settings.py` | Financial multipliers and runtime configuration |
| `pipeline/router.py` | Decision/outcome to impact-type mapping |
| `pipeline/outcome_handler.py` | Per-lead financial-impact calculation |
| `pipeline/impact_evaluator.py` | Deterministic aggregate financial metrics |
| `pipeline/impact_analyzer.py` | Metrics-only AI or simulation interpretation and recommendations |
| `pipeline/ai_processor.py` | Orchestration from deterministic metrics to interpretation |
| `pipeline/validator.py`, `models/` | Input constraints and validation |
| `tests/test_ci.py`, `.github/workflows/ci.yml` | Current automated deterministic verification |
| `database/db.py` | Persistence behaviour |

When these surfaces disagree:

- An adopted ADR governs the material decision it records.
- Documentation states public intent and claims.
- Source code and configuration state implementation behaviour.
- Tests and CI state what is mechanically asserted.
- Surface the disagreement to the owner. Do not silently reconcile it by
  editing one side to match the other.
- If the requested work depends materially on an unresolved conflict, stop
  and ask for owner review before changing anything.

## Task routing

| Task | Start here |
|---|---|
| System description or public claims | `README.md` |
| Input or schema validation | `pipeline/validator.py`, `models/` |
| Decision/outcome mapping | `pipeline/router.py` |
| Per-lead financial calculation | `pipeline/outcome_handler.py`, `config/settings.py` |
| Aggregate metrics | `pipeline/impact_evaluator.py`, `config/settings.py` |
| AI or simulation interpretation, recommendations | `pipeline/impact_analyzer.py` |
| Full impact pipeline orchestration | `pipeline/ai_processor.py` |
| Keyless demo | `seed_and_run.py` (input: `data/sample_outcomes.json`) |
| HTTP API and server startup | `api.py`, `main.py` |
| Persistence | `database/db.py` |
| Architecture decision | `adr/0001-deterministic-scoring-before-ai-layer.md` |
| Tests and deterministic evidence | `tests/test_ci.py`, `.github/workflows/ci.yml` |
| Documentation or artifact validation | the affected artifact, `.githooks/validate_artifacts.py` |
| CI, hooks, publishing | `.github/workflows/ci.yml`, `.githooks/`, `.publicgate-allow` |

## Always-on constraints

1. **Deterministic scoring runs before AI interpretation.** Financial impact
   is computed without an LLM; `pipeline/impact_evaluator.py` imports no
   model client. The AI layer must never become the source of financial
   metrics.
2. **The analyzer receives aggregate `ImpactMetrics` only.** Do not pass raw
   lead records, raw decisions, or outcomes into `pipeline/impact_analyzer.py`.
   `pipeline/ai_processor.py` hands it the metrics object and nothing else.
   This separation is the accepted decision in ADR-0001.
3. **Decision/outcome mapping is explicit and complete.** `pipeline/router.py`
   owns `IMPACT_ROUTING_TABLE`, and every valid combination must be mapped
   there. An unmapped combination must fail loudly: `compute_lead_impact` in
   `pipeline/outcome_handler.py` raises instead of silently defaulting to a
   zero or unknown financial impact. Adding a combination is a code change to
   the table.
4. **Configured multipliers are used consistently.** Per-lead and aggregate
   calculations both read the financial multipliers from
   `config/settings.py`. Do not reintroduce hard-coded constants in the
   aggregate layer that can diverge from configuration.
5. **Delayed-conversion accounting must not double-count its penalty.**
   Delayed revenue enters revenue generated at gross value, and the delay
   penalty is itemized once in revenue lost, so aggregate net impact
   reconciles with the sum of per-lead `financial_impact`.
6. **Pending outcomes are accepted but not evaluated.** A pending record is
   stored and counted as a stored record, carries no financial impact, and is
   excluded from the conversion, false-positive and missed-opportunity rate
   denominators until its outcome is resolved. Preserve the distinction
   between total stored records and records with an evaluable outcome.
7. **Validation runs before persistence on the normal load paths.**
   `seed_and_run.py` and `POST /load` call `validate_batch` before
   `insert_lead`; `insert_lead` itself does not validate, so any new load path
   must validate first. Unknown decision or outcome values, a confidence score
   outside 0.0 to 1.0, a non-positive lead value, or a missing required field
   must not enter as a valid impact record.
8. **AI interpretation cannot overwrite deterministic metrics.** The summary,
   issues, root causes and recommendations may interpret the metrics; the
   financial numbers in the response remain outputs of deterministic scoring.
9. **Keyless simulation is the routine development and verification path.**
   With `USE_SIMULATION_FALLBACK=true` or no API key, `analyze_impact` uses
   the rule-based simulation. Routine tests must stay off paid model calls.
   Real model execution requires explicit owner authorization.
10. **Evaluation assertions are evidence.** Do not change test expectations,
    financial multipliers or constants, sample data, or published failures
    after seeing a run in order to make tests pass. A deliberate change to
    financial assumptions or evaluation evidence requires its own authorized
    task.
11. **Local run output is a runtime artifact.** SQLite databases and other
    output produced by local runs or verification are not committed unless
    separately authorized.
12. **No secrets and no machine-local absolute paths in tracked files.** Keys
    and machine-local values belong in a gitignored local `.env`.
13. **Do not rewrite pushed Git history.**
14. **Trigger-gated artifacts require a genuine material decision record.**
    Documents such as a system walkthrough, changelog or runbook are created
    only when a decision record cites their trigger. ADRs have no hard
    maximum; write one only for a genuine material decision. Version history
    stays in the README Version Log.
15. **This file is guidance, not enforcement.** Tests, hooks, deterministic
    code paths and CI are the enforcement.

## Verification

Routine checks, both keyless:

```bash
python .githooks/validate_artifacts.py .
python -m pytest tests/ -v
```

The artifact validator must print `Tier 0: PASS`.

The test suite is the preferred keyless verification. It forces simulation
fallback, removes `OPENAI_API_KEY` from the environment it runs under, uses
temporary databases, runs the keyless demo, starts the API server and checks
its endpoints, tears the server down, and asserts the deterministic metrics.
No live API key is needed.

The frozen expected values live in `tests/test_ci.py`, and CI runs the same
suite across the operating-system and Python matrix in
`.github/workflows/ci.yml`. Read them there; do not copy them into other
files.
