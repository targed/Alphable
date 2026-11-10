# BRIEFING — 2026-11-09T22:33:00Z

## Mission
Comprehensive codebase, implementation, and bug audit of Alphable V4 (R4 Focus) for the scientific defense against Base MAGPIE and SOTA Scrabble engines.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, investigation, synthesis
- Working directory: /home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_1
- Original parent: d0ac5384-dff3-498c-b189-b11d798c2489
- Milestone: survey-r4-codebase-audit

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes in source code (report findings and propose patches in handoff)
- `.agents/teamwork/` must contain only metadata — no source code or test files
- Self-contained handoff report in `handoff.md`

## Current Parent
- Conversation ID: d0ac5384-dff3-498c-b189-b11d798c2489
- Updated: not yet

## Investigation State
- **Explored paths**: `alphable_v4/` (engine, models, search, platform, training), `cli.py`, `tests/`, `visualizer/tests/`, `vendor/magpie/`, `data/tournaments/`, `docs/`.
- **Key findings**:
  1. Identified 5,475 lines of engine/training code and 1,598 test suite lines.
  2. Verified all 57 core unit tests and 20 visualizer tests pass under pure CPU execution (`CUDA_VISIBLE_DEVICES=""`).
  3. Discovered persistent C heap memory leak in `magpie_bindings.py` (missing `magpie_free_string` calls).
  4. Discovered pre-endgame parity neutralization bug where `cand.tiles_placed` is unpopulated in `from_ucgi_line()`.
  5. Discovered illegal move formatting bug for pass actions in `woogles_bot.py` (`"exchange pass"`).
  6. Discovered 50% jump discontinuity in `BAMSSearch` volatility control formula at $\pm 20$ point margin.
  7. Confirmed "Base MAGPIE" in all historical benchmarks was evaluated solely as 1-ply static KLV equity, omitting native multi-ply simulation and PEG solvers.
- **Unexplored areas**: Empirical head-to-head live simulation against fully-tuned Base MAGPIE and Macondo.

## Key Decisions Made
- Confirmed test suite status: Triton compilation fails in sandbox under CUDA due to missing `Python.h` and read-only `$HOME/.triton`, but 57/57 core tests and 20/20 visualizer tests pass under CPU execution.
- Compiled complete audit report with reproduction commands in `handoff.md`.

## Artifact Index
- DISPATCH.md — Incoming task assignments
- BRIEFING.md — Persistent memory
- progress.md — Liveness heartbeat
- handoff.md — Comprehensive audit report (5-Component format)
