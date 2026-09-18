# STATE — ai-impact-scoring-engine

**Classification:** PROJECT · T0 (decision-intelligence and financial-impact evaluation layer over an existing routing pipeline; `domains/github-ops/CONVENTIONS.md` PROJECT/SYSTEM/EXPERIMENT taxonomy).

**RECONSTRUCTED** (GOVERNANCE.md Build-repo STATE rule, clause 7): derived from git history and the README Version Log at scaffold time (2026-09-19, Q-72(f)), not written contemporaneously. Reconstructed entries are retrospective evidence, not contemporaneous record — the commit that adds this file begins the contemporaneous record going forward.

## Current state

**Status: Complete — v1.0** (README). One ADR: `adr/0001-deterministic-scoring-before-ai-layer.md`.

**README heading correction (this commit, Q-72(f)):** the `## Architecture` heading (previously `## System`) is renamed back to `## System`, aligning with the canonical Tier-0 contract and the sibling engine repos. The substitution was made in commit `34855be` (2026-07-06) — a bundled, unreviewed commit-message rationale attached to an unrelated routing-table bug fix, never recorded as a decision. The anchored-heading regex fix from that same commit (preventing `## System` from false-matching the unrelated `## System Context` footer) is preserved unchanged — only the required heading text reverts.

## Version Log (from README, verbatim)

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2026-04-23 | Initial release — AI Impact & Decision Intelligence Engine (financial evaluation of AI lead-routing decisions) |
| v1.0 | 2026-07-06 | Audit fix (M2): routing table completed to 15/15 valid (decision, outcome) pairs; unmapped combinations now fail loud |
| v1.0 | 2026-07-06 | Audit fix (M1+M3, Option A): aggregate layer's double-counted delay penalty fixed; net impact reconciles exactly with the sum of per-lead `financial_impact` |

## Build history since the Version Log's last entry (from `git log --reverse`)

- **2026-07-11** (`b127fc4`) — CLAUDE.md: session boot + governance pointer.
- **2026-07-24** (`d60951f`) — Canonical pre-commit local-path guard added (Q-48 wave 1).
- **2026-07-27** (`b1a87fd`, `239088a`) — Keyless deterministic CI added (3-OS workflow, Python 3.14 pins bumped); CI badge + coverage note.
- **2026-08-03 – 2026-08-04** (`9b75c6d`, `3690284`, `a571f2a`, `9f8ed53`) — Publish-gate canary; allowlist entry-exact migration; Apache-2.0 license; Q-35 hook rollout.
- **2026-09-15** (`7ee3214`) — Canonical AGENTS.md router adopted (Q-93).
- **2026-09-19** (this commit) — Q-72(f): STATE.md added (this file); README `## System` heading restored per owner ruling (anchored-regex fix preserved); validator's required-section list reverted to `## System`; validator gains a STATE.md-existence check, the obsolete 5-record decision cap is removed, and the six-name BANNED_WITHOUT_TRIGGER list is propagated (live-file precondition checked, clear).

## Open loops

None on disk.
