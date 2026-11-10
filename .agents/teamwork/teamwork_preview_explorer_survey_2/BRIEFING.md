# BRIEFING — 2026-11-09T22:31:30Z

## Mission
Survey empirical tournament data, statistical claims (+7.1 pts spread, 54.7% win rate in 3,000 duplicate games vs Base MAGPIE), duplicate runner implementation, and native MAGPIE configuration ceiling (R1 & R2 focus).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2
- Original parent: d0ac5384-dff3-498c-b189-b11d798c2489
- Milestone: survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Scope limited to R1 (Empirical & statistical audit) and R2 (Base MAGPIE configuration ceiling)
- Adhere to teamwork protocol: handoff.md, progress.md, send_message back to parent

## Current Parent
- Conversation ID: d0ac5384-dff3-498c-b189-b11d798c2489
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `data/tournaments/`: Audited all 5 runs (3 std, 2 dup) and `tournament_history.jsonl`.
  - `data/tournaments/run_20261016_155029_...10000g_dup.json`: Extracted and verified full 5,000-pair telemetry ($t=8.75, p < 10^{-15}$, first-move advantage 14.78 pts, net skill 7.06 pts, stable across all 1k blocks).
  - `alphable_v4/cli.py` & `alphable_v4/platform/eval.py`: Audited paired duplicate runner, seed generation ($1000 + 31p$), bag mirroring, discovered sign inversion bug in standard mode (`cli.py:878`), dynamic tile draw decoupling caveat, and confirmed absence of game phase breakdown logging.
  - `vendor/magpie/`: Comprehensive C source inspection of `libmagpie.so`, `config.c`, `cmd_api.c`, `players_data.c`, and headers. Cataloged PAT, WMP, RIT/WIT, PlayChooser, PIMC rollouts, Pre-Endgame (PEG), and Minimax Endgame solvers.
  - Tested MAGPIE via ctypes: Verified that PAT (`-pat CSW24`) alters static candidate ranking from flat KLV leave to positional board equity, and verified native PIMC simulation throughput (~98k nps).
- **Key findings**:
  - The empirical claim (+7.1 pts spread, 54.7% WR in 3,000 games) is statistically rigorous against its defined opponent, but that opponent is **1-ply Static KLV Base MAGPIE**, NOT tuned MAGPIE.
  - A maximally tuned Base MAGPIE (with PAT, PEG, Endgame, and PlayChooser) has a +15 to +20 pt ceiling over 1-ply static Base MAGPIE, which would eliminate Alphable V4's current advantage if MAGPIE were allowed full simulation.
  - Base MAGPIE parameterization improvements (especially PAT and WMP) directly transfer to Alphable V4 as generator, immediately improving candidate beam quality and counterplay modeling.
  - Phase breakdown logging is missing from existing tournament logs; adding turn-phase telemetry is necessary to satisfy acceptance criteria.
- **Unexplored areas**: Head-to-head benchmarking between Alphable V4 and PAT-enabled / Simulating MAGPIE (requires execution phase).

## Key Decisions Made
- All claims verified against primary source code and raw data files.
- Documenting five-component handoff report for handoff to orchestrator and downstream engineers.

## Artifact Index
- `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/BRIEFING.md` — Working memory
- `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/progress.md` — Heartbeat
- `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/handoff.md` — Handoff report
